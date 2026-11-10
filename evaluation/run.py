"""Capture actual synthetic outputs. Live mode is explicit, bounded and never retried."""
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from time import perf_counter
from unittest.mock import patch

from nyayasaathi.conversation import process_turn
from nyayasaathi.extraction import confirm_fact
from nyayasaathi.llm.base import LLMError, LLMErrorCode
from nyayasaathi.llm.simulated import SimulatedLLM
from nyayasaathi.models import CaseState
from nyayasaathi.retrieval import load_catalogue

ROOT = Path(__file__).resolve().parents[1]


def write(path, data):
    with path.open('x', encoding='utf-8') as output:
        json.dump(data, output, ensure_ascii=False, indent=2, default=str)


def new_run(mode):
    folder = ROOT / 'evaluation' / 'raw_outputs' / (mode + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(parents=True)
    write(folder / 'manifest.json', {
        'mode': mode, 'synthetic_only': True, 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)),
        'catalogue_sha256': sha256((ROOT / 'sources' / 'catalogue.json').read_bytes()).hexdigest(),
        'raw_outputs_are_unedited': True,
    })
    return folder


class RecordedSimulation:
    def __init__(self, failure=None):
        self.failure, self.raw = failure, []

    def generate(self, request):
        if self.failure:
            self.raw.append({'mode': 'mock', 'error': self.failure})
            raise LLMError(LLMErrorCode(self.failure))
        result = SimulatedLLM().generate(request)
        self.raw.append({'model': result.model, 'text': result.text, 'mode': 'offline-simulation'})
        return result


def run_offline():
    folder = new_run('offline')
    for case in json.loads((ROOT / 'evaluation/test_cases/cases.json').read_text(encoding='utf-8')):
        state = CaseState(language=case.get('language', 'en'))
        client = RecordedSimulation(case.get('failure'))
        for index, text in enumerate(case['turns'], 1):
            start = perf_counter()
            previous = state.facts
            count = len(client.raw)
            state = process_turn(state, text, str(index), client, load_catalogue())
            write(folder / f"{case['id']}-{index}.json", {
                'case_id': case['id'], 'mode': 'mock' if case.get('failure') else 'offline-simulation',
                'input': text, 'turn': index, 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                'seconds': round(perf_counter() - start, 4), 'raw_provider': client.raw[count:],
                'state': asdict(state), 'confirmed_preserved': state.facts == previous,
                'note': 'Deterministic simulation or injected failure. NOT live AI.',
            })
            if index == 1:
                for name, value in case.get('confirm', {}).items():
                    state = confirm_fact(state, name, value)
    # A reproducible transcription-failure output, explicitly labelled mock.
    from nyayasaathi.speech import SpeechError
    try:
        raise SpeechError('timeout')
    except SpeechError as error:
        write(folder / 'mock_transcription_failure.json', {'mode': 'mock', 'case_id': 'mock_transcription_failure',
              'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'error': error.code, 'actual_safe_message': str(error)})
    print(folder)
    return folder


def run_live():
    from google import genai
    from streamlit.testing.v1 import AppTest
    from nyayasaathi.config import load_streamlit_settings
    from nyayasaathi.drafting import LABELS
    settings = replace(load_streamlit_settings(dotenv_path=ROOT / '.env'), app_mode='production',
                       llm_max_retries=0, llm_timeout_seconds=90, llm_max_output_tokens=1024)
    settings.require_gemini()
    folder = new_run('live-gemini')
    original = genai.Client
    calls = []

    class ObservedSDK:
        def __init__(self, **kwargs):
            self.client = original(**kwargs)
            self.models = self

        def generate_content(self, **kwargs):
            if len(calls) >= 4:
                raise RuntimeError('Live evaluation request budget exhausted.')
            number = len(calls) + 1
            calls.append(number)
            write(folder / f'call-{number}-started.json', {'attempt': number, 'model': kwargs['model'],
                'timeout_ms': kwargs['config'].http_options.timeout, 'max_output_tokens': kwargs['config'].max_output_tokens,
                'automatic_retries': 0, 'timestamp_utc': datetime.now(timezone.utc).isoformat()})
            record = {'model': kwargs['model'], 'mode': 'live-gemini', 'attempt': number}
            start = perf_counter()
            try:
                result = self.client.models.generate_content(**kwargs)
                record['raw_text'] = result.text
                record['finish_reasons'] = [str(c.finish_reason) for c in result.candidates or []]
                record['usage'] = result.usage_metadata.model_dump(mode='json') if result.usage_metadata else None
                record['api_success'] = True
                return result
            except Exception as error:
                record['api_success'] = False
                record['error_category'] = type(error).__name__
                status = getattr(error, 'code', None)
                record['http_status'] = status if type(status) is int else None
                # Raw exception bodies/headers may include credentials; never capture.
                raise
            finally:
                record['seconds'] = round(perf_counter() - start, 3)
                write(folder / f'call-{number}-response.json', record)

        def close(self):
            self.client.close()

    with patch('nyayasaathi.config.load_streamlit_settings', lambda **_: settings), patch('nyayasaathi.llm.gemini.genai.Client', ObservedSDK):
        for case in json.loads((ROOT / 'evaluation/test_cases/live_cases.json').read_text(encoding='utf-8')):
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=115).run()
            for index, text in enumerate(case['turns'], 1):
                previous = app.session_state.case.facts
                before_calls = len(calls)
                app.chat_input[0].set_value(text).run()
                state = app.session_state.case
                report = {'mode': 'live-gemini', 'case_id': case['id'], 'turn': index, 'input': text,
                          'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'ui_exception': bool(app.exception),
                          'state': asdict(state), 'confirmed_preserved': state.facts == previous,
                          'calls_used': len(calls) - before_calls}
                result = state.last_result
                report['catalogue_only'] = bool(result) and all(any(s.id == c.source_id and s.url == c.url and
                    any(x.id == c.claim_id and x.en == c.text for x in s.claims) for s in load_catalogue()) for c in result.claims)
                count = len(calls)
                app.run()
                report['rerun_preserved'] = app.session_state.case == state
                report['no_duplicate_call'] = len(calls) == count
                write(folder / f"{case['id']}-{index}.json", report)
                print(json.dumps({'case': case['id'], 'turn': index, 'error': result.error if result else 'no_result',
                                  'api_calls_so_far': len(calls), 'confirmed_preserved': report['confirmed_preserved']}), flush=True)
                if index == 1 and state.topic == case['topic'] and not app.exception:
                    for widget in app.text_area:
                        if widget.label in LABELS.values():
                            widget.set_value(case['amount'] if widget.label == LABELS[case['amount_field']] else '')
                    next(b for b in app.button if b.label.startswith('Confirm entered details')).click().run()
                    write(folder / f"{case['id']}-review.json", {'action': 'Explicit synthetic amount confirmation through UI',
                          'field': case['amount_field'], 'value': case['amount'], 'state': asdict(app.session_state.case)})
    print(folder)
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['offline', 'live'], default='offline')
    parser.add_argument('--allow-live', action='store_true')
    args = parser.parse_args()
    if args.mode == 'live' and not args.allow_live:
        parser.error('Live mode requires explicit approval and --allow-live; consumes up to four requests.')
    run_live() if args.mode == 'live' else run_offline()

"""Two explicitly authorized synthetic TTS transcriptions; no Gemini calls."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from time import perf_counter

import groq
from nyayasaathi.config import load_settings
from nyayasaathi.speech import GroqSpeech, SpeechError, validate_audio
from evaluation.run import ROOT, new_run, write


def run():
    settings = load_settings(dotenv_path=ROOT / '.env')
    settings.require_groq()
    folder = new_run('live-groq')
    spoken = {
        'english': 'I bought a mixer grinder online for three thousand five hundred rupees. It arrived damaged. I have the invoice and photos. I want a refund.',
        'hinglish': 'Maine landlord ko twenty thousand rupees security deposit diya tha. Room khaali kar diya, lekin paise wapas nahi mile.',
    }
    for index, (name, script) in enumerate(spoken.items(), 1):
        data = (ROOT / 'tmp/synthetic-audio' / (name + '.wav')).read_bytes()
        duration = validate_audio(data)
        record = {'mode': 'live-groq', 'attempt': index, 'model': settings.groq_model,
                  'input_id': name, 'tts_script': script, 'audio_sha256': sha256(data).hexdigest(),
                  'audio_seconds': duration, 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                  'voice': 'Microsoft Zira Desktop en-US', 'native_hindi_accuracy_verified': False,
                  'automatic_retries': 0, 'timeout_seconds': 30}
        write(folder / (name + '-started.json'), record)
        sdk = groq.Groq(api_key=settings.groq_api_key, max_retries=0, timeout=30)
        original = sdk.audio.transcriptions.create

        def capture(**kwargs):
            response = original(**kwargs)
            record['raw_response'] = response.model_dump(mode='json')
            return response

        sdk.audio.transcriptions.create = capture
        start = perf_counter()
        try:
            record['transcript'] = GroqSpeech(settings, sdk_client=sdk).transcribe(data, consent=True)
            record['success'] = True
        except SpeechError as error:
            record['success'] = False
            record['error'] = error.code
            record['safe_message'] = str(error)
        finally:
            record['seconds'] = round(perf_counter() - start, 3)
            sdk.close()
            write(folder / (name + '.json'), record)
        print({'input': name, 'success': record['success'], 'seconds': record['seconds'], 'error': record.get('error')}, flush=True)
    print(folder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-live', action='store_true')
    args = parser.parse_args()
    if not args.allow_live:
        parser.error('Separate approval required for two live Groq requests; use --allow-live only after approval.')
    run()

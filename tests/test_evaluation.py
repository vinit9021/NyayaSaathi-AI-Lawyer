import json
from unittest.mock import Mock
import pytest
from evaluation import run

pytestmark = pytest.mark.offline


def test_output_writer_never_overwrites_raw_results(tmp_path):
    path = tmp_path / 'raw.json'
    run.write(path, {'text': 'unchanged output'})
    with pytest.raises(FileExistsError):
        run.write(path, {'text': 'replacement'})
    assert json.loads(path.read_text())['text'] == 'unchanged output'


def test_offline_evaluation_captures_actual_modes_and_safety_results(tmp_path, monkeypatch):
    forbidden = Mock(side_effect=AssertionError('No real provider permitted'))
    monkeypatch.setattr('google.genai.Client', forbidden)
    monkeypatch.setattr('groq.Groq', forbidden)
    monkeypatch.setattr(run, 'new_run', lambda mode: tmp_path)
    run.run_offline()
    results = [json.loads(p.read_text(encoding='utf-8')) for p in tmp_path.glob('*.json')]
    assert len(results) == 14
    assert {r['mode'] for r in results} == {'mock', 'offline-simulation'}
    criminal = next(r for r in results if r['case_id'] == 'out_of_scope_criminal')
    assert criminal['state']['blocked'] and not criminal['raw_provider']
    contradictory = next(r for r in results if r['case_id'] == 'contradictory_amount' and r['turn'] == 2)
    assert contradictory['state']['conflicts'] == ['amount_paid']
    assert all(r['confirmed_preserved'] for r in results if 'confirmed_preserved' in r)
    forbidden.assert_not_called()

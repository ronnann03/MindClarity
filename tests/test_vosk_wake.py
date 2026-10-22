import pytest
from voice.vosk_wake import accepts_activation


def result(words):
    return {'result': [dict(word=word, conf=confidence, start=index * .3, end=(index+1)*.3)
                       for index, (word, confidence) in enumerate(words)]}


@pytest.mark.parametrize('words,expected', [
    ([('iu', .98), ('escucha', 1.)], True),
    ([('yu', .90), ('escucha', .92)], True),
    ([('iu', .99)], False),
    ([('escucha', 1.)], False),
    ([('[unk]', 1.), ('yu', 1.), ('escucha', 1.)], False),
    ([('yu', .79), ('escucha', 1.)], False),
    ([('yo', 1.), ('escucha', 1.)], False),
])
def test_complete_activation_is_required(words, expected):
    assert accepts_activation(result(words)) is expected


def test_leading_silence_does_not_prevent_activation():
    data = result([('yu', 1.), ('escucha', 1.)])
    for word in data['result']:
        word['start'] += 30
        word['end'] += 30
    assert accepts_activation(data)


def test_separate_words_do_not_form_an_activation():
    data = result([('yu', 1.), ('escucha', 1.)])
    data['result'][1]['start'] += 3
    assert not accepts_activation(data)

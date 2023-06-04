import tempfile
from pathlib import Path
from unittest import mock

from mypyind.src.constants import DATA_DIR
from mypyind.src.state import MypyindState
from mypyind.src.writer import FilebasedMypyindWriter, WriterConfig


class TestFilebasedMypyindWriter:
    def test_add_found(self):
        state = MypyindState('foo')
        config = WriterConfig(path=DATA_DIR / 'fullnames.txt')
        writer = FilebasedMypyindWriter(state=state, config=config)

        writer.add_if_found(target='foo', from_='bar')

        assert state.is_in_found('foo')

    def test_dump_found(self):
        state = MypyindState('foo')
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            tempfile.NamedTemporaryFile(mode='w', dir=tmpdir, prefix='fullnames', suffix='.txt') as tmpfile,
        ):
            writer_config = WriterConfig(path=tmpfile.name)
            writer = FilebasedMypyindWriter(state=state, config=writer_config)
            writer.add_if_found(target='foo', from_='bar')
            writer.add_if_found(target='foo', from_='baz')

            writer.dump_found()

            assert Path(tmpfile.name).read_text() == 'foo\nbar\nbaz\n'

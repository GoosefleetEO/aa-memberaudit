from pathlib import Path

from app_utils.testing import NoSocketsTestCase

from ..core.eft_parser import Fitting
from .testdata.load_eveuniverse import load_eveuniverse


class TestEftParser(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()
        testdata_folder = Path(__file__).parent / "testdata"
        svipul_fitting_file = testdata_folder / "fitting_svipul.txt"
        with svipul_fitting_file.open("r") as fp:
            cls.svipul_fitting = fp.read()

    def test_should_read_fitting(self):
        result = Fitting.create_from_eft(self.svipul_fitting)
        print(result)
        print([obj.name for obj in result.main_types()])

from app_utils.testing import NoSocketsTestCase

from ..core.xml_converter import eve_xml_to_html
from .testdata.load_entities import load_entities
from .testdata.load_eveuniverse import load_eveuniverse
from .testdata.load_locations import load_locations

MODULE_PATH = "memberaudit.core.xml_converter"


class TestXMLConversion(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()
        load_entities()
        load_locations()

    def test_should_convert_font_tag(self):
        input = '<font size="13" color="#b3ffffff">Character</font>'
        expected = '<span style="font-size: 13px">Character</span>'
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_remove_loc_tag(self):
        input = "<loc>Character</loc>"
        expected = "Character"
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_add_target_to_normal_links(self):
        input = (
            '<a href="http://www.google.com" target="_blank">https://www.google.com</a>'
        )
        self.assertHTMLEqual(eve_xml_to_html(input), input)

    def test_should_convert_character_link(self):
        input = '<a href="showinfo:1376//1001">Bruce Wayne</a>'
        expected = '<a href="https://evewho.com/character/1001" target="_blank">Bruce Wayne</a>'
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_convert_corporation_link(self):
        input = '<a href="showinfo:2//2001">Wayne Technologies</a>'
        expected = (
            '<a href="https://evemaps.dotlan.net/corp/Wayne_Technologies" '
            'target="_blank">Wayne Technologies</a>'
        )
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_convert_alliance_link(self):
        input = '<a href="showinfo:16159//3001">Wayne Enterprises</a>'
        expected = (
            '<a href="https://evemaps.dotlan.net/alliance/Wayne_Enterprises" '
            'target="_blank">Wayne Enterprises</a>'
        )
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_convert_solar_system_link(self):
        input = '<a href="showinfo:5//30004984">Abune</a>'
        expected = '<a href="https://evemaps.dotlan.net/system/Abune" target="_blank">Abune</a>'
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_convert_station_link(self):
        input = (
            '<a href="showinfo:52678//60003760">'
            "Jita IV - Moon 4 - Caldari Navy Assembly Plant</a>"
        )
        expected = (
            '<a href="https://evemaps.dotlan.net/station/Jita_IV_-_Moon_4_-_Caldari_Navy_Assembly_Plant" '
            'target="_blank">Jita IV - Moon 4 - Caldari Navy Assembly Plant</a>'
        )
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_convert_kill_link(self):
        input = (
            '<a href="killReport:84900666:9e6fe9e5392ff0cfc6ab956677dbe1deb69c4b04">'
            "Kill: Yuna Kobayashi (Badger)</a>"
        )
        expected = (
            '<a href="https://zkillboard.com/kill/84900666/" '
            'target="_blank">Kill: Yuna Kobayashi (Badger)</a>'
        )
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    # def test_should_disable_unknown_types(self):
    #     input = '<a href="showinfo:601//30004984">Abune</a>'
    #     expected = '<a href="#">Abune</a>'
    #     self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_disable_unknown_links(self):
        input = '<a href="unknown">Abune</a>'
        expected = '<a href="#">Abune</a>'
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_set_default_font(self):
        input = 'First<br><span style="font-size: 20px">Second</span>Third'
        expected = (
            '<span style="font-size: 13px">First</span>'
            '<br><span style="font-size: 20px">Second</span>'
            '<span style="font-size: 13px">Third</span>'
        )
        self.assertHTMLEqual(eve_xml_to_html(input, add_default_style=True), expected)

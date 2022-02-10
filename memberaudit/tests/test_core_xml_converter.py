from unittest.mock import Mock, patch

from eveuniverse.core import dotlan, evewho

from app_utils.testing import NoSocketsTestCase

from ..core.xml_converter import eve_xml_to_html
from .testdata.esi_client_stub import load_test_data
from .testdata.load_entities import load_entities
from .testdata.load_eveuniverse import load_eveuniverse

MODULE_PATH = "memberaudit.core.xml_converter"


class TestXMLConversion(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()
        load_entities()

    def test_convert_eve_xml_alliance(self):
        """can convert an alliance link in CCP XML to HTML"""
        with patch(
            "eveuniverse.models.EveEntity.objects.resolve_name",
            Mock(return_value="An Alliance"),
        ):
            result = eve_xml_to_html(
                load_test_data()
                .get("Mail")
                .get("get_characters_character_id_mail_mail_id")
                .get("2")
                .get("body")
            )
            self.assertTrue(result.find(dotlan.alliance_url("An Alliance")) != -1)

    def test_convert_eve_xml_character(self):
        """can convert a character link in CCP XML to HTML"""
        result = eve_xml_to_html(
            load_test_data()
            .get("Mail")
            .get("get_characters_character_id_mail_mail_id")
            .get("2")
            .get("body")
        )
        self.assertTrue(result.find(evewho.character_url(1001)) != -1)

    def test_convert_eve_xml_corporation(self):
        """can convert a corporation link in CCP XML to HTML"""
        with patch(
            "eveuniverse.models.EveEntity.objects.resolve_name",
            Mock(return_value="A Corporation"),
        ):
            result = eve_xml_to_html(
                load_test_data()
                .get("Mail")
                .get("get_characters_character_id_mail_mail_id")
                .get("2")
                .get("body")
            )
            self.assertTrue(result.find(dotlan.alliance_url("A Corporation")) != -1)

    def test_convert_eve_xml_solar_system(self):
        """can convert a solar system link in CCP XML to HTML"""
        with patch(
            "eveuniverse.models.EveEntity.objects.resolve_name",
            Mock(return_value="Polaris"),
        ):
            result = eve_xml_to_html(
                load_test_data()
                .get("Mail")
                .get("get_characters_character_id_mail_mail_id")
                .get("2")
                .get("body")
            )
            self.assertTrue(result.find(dotlan.solar_system_url("Polaris")) != -1)

    def test_convert_bio_1(self):
        """can convert a bio includes lots of non-ASCII characters and handle the u-bug"""
        with patch(
            "eveuniverse.models.EveEntity.objects.resolve_name",
            Mock(return_value="An Alliance"),
        ):
            result = eve_xml_to_html(
                load_test_data()
                .get("Character")
                .get("get_characters_character_id")
                .get("1002")
                .get("description")
            )
            self.assertIn(
                "Zuverlässigkeit, Eigeninitiative, Hilfsbereitschaft, Teamfähigkeit",
                result,
            )
            self.assertNotEqual(result[:2], "u'")

    def test_convert_bio_2(self):
        """can convert a bio that resulted in a syntax error (#77)"""
        with patch(
            "eveuniverse.models.EveEntity.objects.resolve_name",
            Mock(return_value="An Alliance"),
        ):
            try:
                result = eve_xml_to_html(
                    load_test_data()
                    .get("Character")
                    .get("get_characters_character_id")
                    .get("1003")
                    .get("description")
                )
            except Exception as ex:
                self.fail(f"Unexpected exception was raised: {ex}")

            self.assertNotEqual(result[:2], "u'")

    def test_convert_bio_3(self):
        """can convert a bio includes lots of non-ASCII characters and handle the u-bug"""
        result = eve_xml_to_html(
            load_test_data()
            .get("Character")
            .get("get_characters_character_id")
            .get("1099")
            .get("description")
        )
        self.assertNotEqual(result[:2], "u'")


class TestXMLConversion2(NoSocketsTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        load_eveuniverse()
        load_entities()

    def test_should_convert_font_tag(self):
        input = """<font size="13" color="#b3ffffff">Character</font>"""
        expected = """<span style="font-size: 13px">Character</span>"""
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_remove_loc_tag(self):
        input = """<loc>Character</loc>"""
        expected = """Character"""
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_add_target_to_normal_links(self):
        input = """<a href="http://www.google.com" target="_blank">https://www.google.com</a>"""
        self.assertHTMLEqual(eve_xml_to_html(input), input)

    def test_should_convert_character_link(self):
        input = """<a href="showinfo:1376//1001">Bruce Wayne</a>"""
        expected = """<a href="https://evewho.com/character/1001" target="_blank">Bruce Wayne</a>"""
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_convert_corporation_link(self):
        input = """<a href="showinfo:2//2001">Wayne Technologies</a>"""
        expected = """<a href="https://evemaps.dotlan.net/corp/Wayne_Technologies" target="_blank">Wayne Technologies</a>"""
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_convert_alliance_link(self):
        input = """<a href="showinfo:16159//3001">Wayne Enterprises</a>"""
        expected = """<a href="https://evemaps.dotlan.net/alliance/Wayne_Enterprises" target="_blank">Wayne Enterprises</a>"""
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_convert_solar_system_link(self):
        input = """<a href="showinfo:5//30004984">Abune</a>"""
        expected = """<a href="https://evemaps.dotlan.net/system/Abune" target="_blank">Abune</a>"""
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_convert_kill_link(self):
        input = """<a href="killReport:84900666:9e6fe9e5392ff0cfc6ab956677dbe1deb69c4b04">Kill: Yuna Kobayashi (Badger)</a>"""
        expected = """<a href="https://zkillboard.com/kill/84900666/" target="_blank">Kill: Yuna Kobayashi (Badger)</a>"""
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_disable_unknown_types(self):
        input = """<a href="showinfo:666//30004984">Abune</a>"""
        expected = """<a href="#">Abune</a>"""
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_disable_unknown_links(self):
        input = """<a href="unknown">Abune</a>"""
        expected = """<a href="#">Abune</a>"""
        self.assertHTMLEqual(eve_xml_to_html(input), expected)

    def test_should_set_default_font(self):
        input = 'First<br><span style="font-size: 20px">Second</span>Third'
        expected = (
            '<span style="font-size: 13px">First</span>'
            '<br><span style="font-size: 20px">Second</span>'
            '<span style="font-size: 13px">Third</span>'
        )
        self.assertHTMLEqual(eve_xml_to_html(input, add_default_style=True), expected)

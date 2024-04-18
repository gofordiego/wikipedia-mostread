from collections import namedtuple
from datetime import datetime, timedelta
import logging
import os
import sys
from unittest import IsolatedAsyncioTestCase, main

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import shared.wiki_api as wiki_api


class WikiAPITests(IsolatedAsyncioTestCase):

    def setUp(self):
        self.wiki_api = wiki_api.WikiAPI()

    async def test_fetch_most_read_articles_success(self):
        """Test `fetch_most_read_articles` success."""

        # Calculate tomorrow's date for testing
        tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")

        Case = namedtuple(
            "Case", ("lang_code", "start", "end", "test_message", "expected_mostread")
        )
        cases = [
            Case(
                "en",
                "2024-02-19",
                "2024-02-19",
                "Test 1-day range",
                self.EXPECTED_MOST_READ_EN_20240219,
            ),
            Case(
                "en",
                "2024-02-19",
                "2024-02-20",
                "Test 2-day range",
                self.EXPECTED_MOST_READ_EN_20240219_20240220,
            ),
            Case(
                "es",
                "2024-02-19",
                "2024-02-19",
                "Test other language code",
                self.EXPECTED_MOST_READ_ES_20240219,
            ),
            # Tomorrow's page views do not exist yet, however API returns 200 response for other scheduled Featured Content.
            Case("en", tomorrow, tomorrow, "Test future date", []),
        ]

        for c in cases:
            results = await self.wiki_api.fetch_most_read_articles(
                lang_code=c.lang_code, start=c.start, end=c.end
            )
            expected_results = {
                "data": c.expected_mostread,
                "errors": [],
            }
            self.assertEqual(results, expected_results, "Test returned articles")

    async def test_fetch_most_read_articles_raised_exceptions(self):
        """Test `fetch_most_read_articles` raised exceptions."""

        Case = namedtuple("Case", ("lang_code", "start", "end", "expected_exception"))
        cases = [
            Case("en", "2024-19-02", "2024-02-19", wiki_api.InvalidStartDateError),
            Case("es", "2024-02-19", "2024-19-02", wiki_api.InvalidEndDateError),
            Case("es", "2024-02-20", "2024-02-19", wiki_api.InvalidDateRangeError),
            Case(
                "hax0r.com/pwned",
                "2024-02-19",
                "2024-02-19",
                wiki_api.InvalidLanguageCodeError,
            ),
        ]

        for c in cases:
            with self.assertRaises(c.expected_exception) as cm:
                await self.wiki_api.fetch_most_read_articles(
                    lang_code=c.lang_code, start=c.start, end=c.end
                )
            # Check also the base module error is reported correctly.
            self.assertIsInstance(cm.exception, wiki_api.WikiAPIError)

    async def test_fetch_most_read_articles_response_errors(self):
        """Test `fetch_most_read_articles` response errors."""

        Case = namedtuple(
            "Case",
            (
                "lang_code",
                "start",
                "end",
                "expected_error_url",
                "expected_error_message",
            ),
        )
        cases = [
            # Host fails for non-existent language codes.
            Case(
                "valyrian",
                "2024-02-19",
                "2024-02-19",
                "https://valyrian.wikipedia.org/api/rest_v1/feed/featured/2024/02/20",
                str(wiki_api.WikipediaConnectionError()),
            ),
            # A thousand years in the future response an error response.
            Case(
                "en",
                "3024-02-19",
                "3024-02-19",
                "https://en.wikipedia.org/api/rest_v1/feed/featured/3024/02/20",
                str(wiki_api.WikipediaResponseError()),
            ),
        ]

        for c in cases:
            results = await self.wiki_api.fetch_most_read_articles(
                lang_code=c.lang_code, start=c.start, end=c.end
            )
            expected_results = {
                "data": [],
                "errors": [
                    {
                        "url": c.expected_error_url,
                        "message": c.expected_error_message,
                    },
                ],
            }
            self.assertEqual(results, expected_results, "Test returned errors")

    # MARK - Expected Values

    # TODO: All these could be moved to a test constants file leaving them here for simplicity.
    EXPECTED_MOST_READ_EN_20240219 = [
        {
            "page": "https://en.wikipedia.org/wiki/Alexei_Navalny",
            "total_views": 273796,
            "view_history": [{"date": "2024-02-19", "views": 273796}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Madame_Web_(film)",
            "total_views": 243590,
            "view_history": [{"date": "2024-02-19", "views": 243590}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/J._Robert_Oppenheimer",
            "total_views": 236434,
            "view_history": [{"date": "2024-02-19", "views": 236434}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/True_Detective_season_4",
            "total_views": 211326,
            "view_history": [{"date": "2024-02-19", "views": 211326}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Cillian_Murphy",
            "total_views": 140124,
            "view_history": [{"date": "2024-02-19", "views": 140124}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Oppenheimer_(film)",
            "total_views": 137469,
            "view_history": [{"date": "2024-02-19", "views": 137469}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Bob_Marley",
            "total_views": 136699,
            "view_history": [{"date": "2024-02-19", "views": 136699}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Presidents'_Day",
            "total_views": 133930,
            "view_history": [{"date": "2024-02-19", "views": 133930}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Deaths_in_2024",
            "total_views": 127488,
            "view_history": [{"date": "2024-02-19", "views": 127488}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Griselda_Blanco",
            "total_views": 118535,
            "view_history": [{"date": "2024-02-19", "views": 118535}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Lenny_Kravitz",
            "total_views": 112402,
            "view_history": [{"date": "2024-02-19", "views": 112402}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Taylor_Swift",
            "total_views": 106192,
            "view_history": [{"date": "2024-02-19", "views": 106192}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Sydney_Sweeney",
            "total_views": 103223,
            "view_history": [{"date": "2024-02-19", "views": 103223}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Blake_Proehl",
            "total_views": 102782,
            "view_history": [{"date": "2024-02-19", "views": 102782}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Shivaji",
            "total_views": 89104,
            "view_history": [{"date": "2024-02-19", "views": 89104}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/NBA_All-Star_Game",
            "total_views": 88624,
            "view_history": [{"date": "2024-02-19", "views": 88624}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/ChatGPT",
            "total_views": 86999,
            "view_history": [{"date": "2024-02-19", "views": 86999}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Sabrina_Ionescu",
            "total_views": 86933,
            "view_history": [{"date": "2024-02-19", "views": 86933}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Albert_Einstein",
            "total_views": 85638,
            "view_history": [{"date": "2024-02-19", "views": 85638}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Jarom%C3%ADr_J%C3%A1gr",
            "total_views": 84901,
            "view_history": [{"date": "2024-02-19", "views": 84901}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Pakistan_Super_League",
            "total_views": 84812,
            "view_history": [{"date": "2024-02-19", "views": 84812}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Elizabeth_Riddle_Graves",
            "total_views": 83842,
            "view_history": [{"date": "2024-02-19", "views": 83842}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Laverne_Cox",
            "total_views": 82259,
            "view_history": [{"date": "2024-02-19", "views": 82259}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Poor_Things_(film)",
            "total_views": 81588,
            "view_history": [{"date": "2024-02-19", "views": 81588}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/77th_British_Academy_Film_Awards",
            "total_views": 79936,
            "view_history": [{"date": "2024-02-19", "views": 79936}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Michael_J._Fox",
            "total_views": 79679,
            "view_history": [{"date": "2024-02-19", "views": 79679}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Helldivers_2",
            "total_views": 76726,
            "view_history": [{"date": "2024-02-19", "views": 76726}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Ilia_Topuria",
            "total_views": 74151,
            "view_history": [{"date": "2024-02-19", "views": 74151}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/One_Day_(TV_series)",
            "total_views": 73437,
            "view_history": [{"date": "2024-02-19", "views": 73437}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/True_Detective",
            "total_views": 72720,
            "view_history": [{"date": "2024-02-19", "views": 72720}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Von_Erich_family",
            "total_views": 69409,
            "view_history": [{"date": "2024-02-19", "views": 69409}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Mac_McClung",
            "total_views": 68439,
            "view_history": [{"date": "2024-02-19", "views": 68439}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/2024_NBA_All-Star_Game",
            "total_views": 68320,
            "view_history": [{"date": "2024-02-19", "views": 68320}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Bramayugam",
            "total_views": 67797,
            "view_history": [{"date": "2024-02-19", "views": 67797}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Yulia_Navalnaya",
            "total_views": 67736,
            "view_history": [{"date": "2024-02-19", "views": 67736}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Kiribati",
            "total_views": 67280,
            "view_history": [{"date": "2024-02-19", "views": 67280}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Oliver_Glasner",
            "total_views": 66999,
            "view_history": [{"date": "2024-02-19", "views": 66999}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Demon_core",
            "total_views": 66346,
            "view_history": [{"date": "2024-02-19", "views": 66346}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Kali_Reis",
            "total_views": 63940,
            "view_history": [{"date": "2024-02-19", "views": 63940}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/The_Beekeeper_(2024_film)",
            "total_views": 63541,
            "view_history": [{"date": "2024-02-19", "views": 63541}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Anyone_but_You",
            "total_views": 61485,
            "view_history": [{"date": "2024-02-19", "views": 61485}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Dakota_Johnson",
            "total_views": 61352,
            "view_history": [{"date": "2024-02-19", "views": 61352}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Madame_Web",
            "total_views": 61273,
            "view_history": [{"date": "2024-02-19", "views": 61273}],
        },
    ]

    EXPECTED_MOST_READ_EN_20240219_20240220 = [
        {
            "page": "https://en.wikipedia.org/wiki/Alexei_Navalny",
            "total_views": 479302,
            "view_history": [
                {"date": "2024-02-19", "views": 273796},
                {"date": "2024-02-20", "views": 205506},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Madame_Web_(film)",
            "total_views": 438567,
            "view_history": [
                {"date": "2024-02-19", "views": 243590},
                {"date": "2024-02-20", "views": 194977},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/J._Robert_Oppenheimer",
            "total_views": 368804,
            "view_history": [
                {"date": "2024-02-19", "views": 236434},
                {"date": "2024-02-20", "views": 132370},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/True_Detective_season_4",
            "total_views": 347692,
            "view_history": [
                {"date": "2024-02-19", "views": 211326},
                {"date": "2024-02-20", "views": 136366},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Robin_Windsor",
            "total_views": 346246,
            "view_history": [{"date": "2024-02-20", "views": 346246}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Deaths_in_2024",
            "total_views": 265945,
            "view_history": [
                {"date": "2024-02-19", "views": 127488},
                {"date": "2024-02-20", "views": 138457},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Rituraj_Singh_(actor)",
            "total_views": 241803,
            "view_history": [{"date": "2024-02-20", "views": 241803}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Bob_Marley",
            "total_views": 235055,
            "view_history": [
                {"date": "2024-02-19", "views": 136699},
                {"date": "2024-02-20", "views": 98356},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Saturn_Devouring_His_Son",
            "total_views": 228418,
            "view_history": [{"date": "2024-02-20", "views": 228418}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Oppenheimer_(film)",
            "total_views": 217915,
            "view_history": [
                {"date": "2024-02-19", "views": 137469},
                {"date": "2024-02-20", "views": 80446},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Griselda_Blanco",
            "total_views": 211672,
            "view_history": [
                {"date": "2024-02-19", "views": 118535},
                {"date": "2024-02-20", "views": 93137},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Cillian_Murphy",
            "total_views": 199919,
            "view_history": [
                {"date": "2024-02-19", "views": 140124},
                {"date": "2024-02-20", "views": 59795},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Kagney_Linn_Karter",
            "total_views": 192162,
            "view_history": [{"date": "2024-02-20", "views": 192162}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Taylor_Swift",
            "total_views": 189084,
            "view_history": [
                {"date": "2024-02-19", "views": 106192},
                {"date": "2024-02-20", "views": 82892},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Bridgit_Mendler",
            "total_views": 187708,
            "view_history": [{"date": "2024-02-20", "views": 187708}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/David_McCallum",
            "total_views": 186303,
            "view_history": [{"date": "2024-02-20", "views": 186303}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Sydney_Sweeney",
            "total_views": 182662,
            "view_history": [
                {"date": "2024-02-19", "views": 103223},
                {"date": "2024-02-20", "views": 79439},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/ChatGPT",
            "total_views": 180017,
            "view_history": [
                {"date": "2024-02-19", "views": 86999},
                {"date": "2024-02-20", "views": 93018},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Pakistan_Super_League",
            "total_views": 162797,
            "view_history": [
                {"date": "2024-02-19", "views": 84812},
                {"date": "2024-02-20", "views": 77985},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Albert_Einstein",
            "total_views": 149786,
            "view_history": [
                {"date": "2024-02-19", "views": 85638},
                {"date": "2024-02-20", "views": 64148},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Helldivers_2",
            "total_views": 147881,
            "view_history": [
                {"date": "2024-02-19", "views": 76726},
                {"date": "2024-02-20", "views": 71155},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Kiribati",
            "total_views": 145313,
            "view_history": [
                {"date": "2024-02-19", "views": 67280},
                {"date": "2024-02-20", "views": 78033},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/One_Day_(TV_series)",
            "total_views": 141021,
            "view_history": [
                {"date": "2024-02-19", "views": 73437},
                {"date": "2024-02-20", "views": 67584},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Presidents'_Day",
            "total_views": 133930,
            "view_history": [{"date": "2024-02-19", "views": 133930}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/True_Detective",
            "total_views": 128848,
            "view_history": [
                {"date": "2024-02-19", "views": 72720},
                {"date": "2024-02-20", "views": 56128},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Anyone_but_You",
            "total_views": 119547,
            "view_history": [
                {"date": "2024-02-19", "views": 61485},
                {"date": "2024-02-20", "views": 58062},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Andreas_Brehme",
            "total_views": 118261,
            "view_history": [{"date": "2024-02-20", "views": 118261}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Dakota_Johnson",
            "total_views": 116913,
            "view_history": [
                {"date": "2024-02-19", "views": 61352},
                {"date": "2024-02-20", "views": 55561},
            ],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Tom_Lehrer",
            "total_views": 114899,
            "view_history": [{"date": "2024-02-20", "views": 114899}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Lenny_Kravitz",
            "total_views": 112402,
            "view_history": [{"date": "2024-02-19", "views": 112402}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Julian_Assange",
            "total_views": 106848,
            "view_history": [{"date": "2024-02-20", "views": 106848}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Blake_Proehl",
            "total_views": 102782,
            "view_history": [{"date": "2024-02-19", "views": 102782}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Luis_Garavito",
            "total_views": 101522,
            "view_history": [{"date": "2024-02-20", "views": 101522}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Sam_Bankman-Fried",
            "total_views": 92385,
            "view_history": [{"date": "2024-02-20", "views": 92385}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/UEFA_Champions_League",
            "total_views": 89211,
            "view_history": [{"date": "2024-02-20", "views": 89211}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Shivaji",
            "total_views": 89104,
            "view_history": [{"date": "2024-02-19", "views": 89104}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/NBA_All-Star_Game",
            "total_views": 88624,
            "view_history": [{"date": "2024-02-19", "views": 88624}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Sabrina_Ionescu",
            "total_views": 86933,
            "view_history": [{"date": "2024-02-19", "views": 86933}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Jarom%C3%ADr_J%C3%A1gr",
            "total_views": 84901,
            "view_history": [{"date": "2024-02-19", "views": 84901}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Elizabeth_Riddle_Graves",
            "total_views": 83842,
            "view_history": [{"date": "2024-02-19", "views": 83842}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Laverne_Cox",
            "total_views": 82259,
            "view_history": [{"date": "2024-02-19", "views": 82259}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Poor_Things_(film)",
            "total_views": 81588,
            "view_history": [{"date": "2024-02-19", "views": 81588}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/77th_British_Academy_Film_Awards",
            "total_views": 79936,
            "view_history": [{"date": "2024-02-19", "views": 79936}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Michael_J._Fox",
            "total_views": 79679,
            "view_history": [{"date": "2024-02-19", "views": 79679}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Ilia_Topuria",
            "total_views": 74151,
            "view_history": [{"date": "2024-02-19", "views": 74151}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Ruby_Franke",
            "total_views": 73284,
            "view_history": [{"date": "2024-02-20", "views": 73284}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Von_Erich_family",
            "total_views": 69409,
            "view_history": [{"date": "2024-02-19", "views": 69409}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Mac_McClung",
            "total_views": 68439,
            "view_history": [{"date": "2024-02-19", "views": 68439}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/2024_NBA_All-Star_Game",
            "total_views": 68320,
            "view_history": [{"date": "2024-02-19", "views": 68320}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Bramayugam",
            "total_views": 67797,
            "view_history": [{"date": "2024-02-19", "views": 67797}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Yulia_Navalnaya",
            "total_views": 67736,
            "view_history": [{"date": "2024-02-19", "views": 67736}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Oliver_Glasner",
            "total_views": 66999,
            "view_history": [{"date": "2024-02-19", "views": 66999}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Demon_core",
            "total_views": 66346,
            "view_history": [{"date": "2024-02-19", "views": 66346}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Kali_Reis",
            "total_views": 63940,
            "view_history": [{"date": "2024-02-19", "views": 63940}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/The_Beekeeper_(2024_film)",
            "total_views": 63541,
            "view_history": [{"date": "2024-02-19", "views": 63541}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Elimination_Chamber%3A_Perth",
            "total_views": 63040,
            "view_history": [{"date": "2024-02-20", "views": 63040}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Virat_Kohli",
            "total_views": 61536,
            "view_history": [{"date": "2024-02-20", "views": 61536}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Madame_Web",
            "total_views": 61273,
            "view_history": [{"date": "2024-02-19", "views": 61273}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Marcus_Collins",
            "total_views": 61112,
            "view_history": [{"date": "2024-02-20", "views": 61112}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/William_Byron_(racing_driver)",
            "total_views": 60393,
            "view_history": [{"date": "2024-02-20", "views": 60393}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Porno_y_helado",
            "total_views": 60373,
            "view_history": [{"date": "2024-02-20", "views": 60373}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Danny_Masterson",
            "total_views": 60030,
            "view_history": [{"date": "2024-02-20", "views": 60030}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Facebook",
            "total_views": 59044,
            "view_history": [{"date": "2024-02-20", "views": 59044}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Borderlands_(film)",
            "total_views": 58227,
            "view_history": [{"date": "2024-02-20", "views": 58227}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Aurus_Senat",
            "total_views": 57649,
            "view_history": [{"date": "2024-02-20", "views": 57649}],
        },
        {
            "page": "https://en.wikipedia.org/wiki/Premier_League",
            "total_views": 57420,
            "view_history": [{"date": "2024-02-20", "views": 57420}],
        },
    ]

    EXPECTED_MOST_READ_ES_20240219 = [
        {
            "page": "https://es.wikipedia.org/wiki/Ilia_Topuria",
            "total_views": 120474,
            "view_history": [{"date": "2024-02-19", "views": 120474}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Cleopatra_I_de_Egipto",
            "total_views": 96034,
            "view_history": [{"date": "2024-02-19", "views": 96034}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Griselda_Blanco",
            "total_views": 30803,
            "view_history": [{"date": "2024-02-19", "views": 30803}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Conor_McGregor",
            "total_views": 25764,
            "view_history": [{"date": "2024-02-19", "views": 25764}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Tabla_peri%C3%B3dica_de_los_elementos",
            "total_views": 25112,
            "view_history": [{"date": "2024-02-19", "views": 25112}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Madame_Web_(pel%C3%ADcula)",
            "total_views": 24609,
            "view_history": [{"date": "2024-02-19", "views": 24609}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Kylian_Mbapp%C3%A9",
            "total_views": 23879,
            "view_history": [{"date": "2024-02-19", "views": 23879}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Albert_Einstein",
            "total_views": 23208,
            "view_history": [{"date": "2024-02-19", "views": 23208}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/ChatGPT",
            "total_views": 22903,
            "view_history": [{"date": "2024-02-19", "views": 22903}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Elecciones_generales_de_la_Rep%C3%BAblica_Dominicana_de_2024",
            "total_views": 21679,
            "view_history": [{"date": "2024-02-19", "views": 21679}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Girona_F%C3%BAtbol_Club",
            "total_views": 20946,
            "view_history": [{"date": "2024-02-19", "views": 20946}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Alexander_Volkanovski",
            "total_views": 19645,
            "view_history": [{"date": "2024-02-19", "views": 19645}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Aleks%C3%A9i_Navalni",
            "total_views": 18587,
            "view_history": [{"date": "2024-02-19", "views": 18587}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Elecciones_al_Parlamento_de_Galicia_de_2024",
            "total_views": 18424,
            "view_history": [{"date": "2024-02-19", "views": 18424}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Aleksandre_Topuria",
            "total_views": 18055,
            "view_history": [{"date": "2024-02-19", "views": 18055}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Bloque_Nacionalista_Galego",
            "total_views": 17673,
            "view_history": [{"date": "2024-02-19", "views": 17673}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Vuelo_571_de_la_Fuerza_A%C3%A9rea_Uruguaya",
            "total_views": 15094,
            "view_history": [{"date": "2024-02-19", "views": 15094}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Marcelo_Barovero",
            "total_views": 14645,
            "view_history": [{"date": "2024-02-19", "views": 14645}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Bob_Marley",
            "total_views": 14389,
            "view_history": [{"date": "2024-02-19", "views": 14389}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Democracia_Ourensana",
            "total_views": 13588,
            "view_history": [{"date": "2024-02-19", "views": 13588}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Operaci%C3%B3n_Triunfo_2023",
            "total_views": 13555,
            "view_history": [{"date": "2024-02-19", "views": 13555}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/All-Star_Game_de_la_NBA_2024",
            "total_views": 13095,
            "view_history": [{"date": "2024-02-19", "views": 13095}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Rodrigo_Pardo_Garc%C3%ADa-Pe%C3%B1a",
            "total_views": 12890,
            "view_history": [{"date": "2024-02-19", "views": 12890}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Alfonso_Rueda",
            "total_views": 12757,
            "view_history": [{"date": "2024-02-19", "views": 12757}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Madame_Web",
            "total_views": 12584,
            "view_history": [{"date": "2024-02-19", "views": 12584}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Primera_Guerra_Mundial",
            "total_views": 12269,
            "view_history": [{"date": "2024-02-19", "views": 12269}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Ultimate_Fighting_Championship",
            "total_views": 12162,
            "view_history": [{"date": "2024-02-19", "views": 12162}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Fernando_Delgado_(periodista_y_escritor)",
            "total_views": 12072,
            "view_history": [{"date": "2024-02-19", "views": 12072}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Sydney_Sweeney",
            "total_views": 12051,
            "view_history": [{"date": "2024-02-19", "views": 12051}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Sim%C3%B3n_Bol%C3%ADvar",
            "total_views": 11926,
            "view_history": [{"date": "2024-02-19", "views": 11926}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Liga_de_Campeones_de_la_UEFA",
            "total_views": 11826,
            "view_history": [{"date": "2024-02-19", "views": 11826}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/La_sociedad_de_la_nieve",
            "total_views": 11542,
            "view_history": [{"date": "2024-02-19", "views": 11542}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/XXX_2%3A_estado_de_emergencias",
            "total_views": 11130,
            "view_history": [{"date": "2024-02-19", "views": 11130}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Arroba_(s%C3%ADmbolo)",
            "total_views": 10865,
            "view_history": [{"date": "2024-02-19", "views": 10865}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Club_Atl%C3%A9tico_Boca_Juniors",
            "total_views": 10556,
            "view_history": [{"date": "2024-02-19", "views": 10556}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/19_de_febrero",
            "total_views": 10484,
            "view_history": [{"date": "2024-02-19", "views": 10484}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Cristiano_Ronaldo",
            "total_views": 10419,
            "view_history": [{"date": "2024-02-19", "views": 10419}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Espa%C3%B1a",
            "total_views": 10061,
            "view_history": [{"date": "2024-02-19", "views": 10061}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Ana_Pont%C3%B3n",
            "total_views": 10051,
            "view_history": [{"date": "2024-02-19", "views": 10051}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Operaci%C3%B3n_Triunfo_(Espa%C3%B1a)",
            "total_views": 9956,
            "view_history": [{"date": "2024-02-19", "views": 9956}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Segunda_Guerra_Mundial",
            "total_views": 9908,
            "view_history": [{"date": "2024-02-19", "views": 9908}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Lionel_Messi",
            "total_views": 9357,
            "view_history": [{"date": "2024-02-19", "views": 9357}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Pobres_criaturas",
            "total_views": 8968,
            "view_history": [{"date": "2024-02-19", "views": 8968}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/WhatsApp",
            "total_views": 8908,
            "view_history": [{"date": "2024-02-19", "views": 8908}],
        },
        {
            "page": "https://es.wikipedia.org/wiki/Jabib_Nurmagom%C3%A9dov",
            "total_views": 8893,
            "view_history": [{"date": "2024-02-19", "views": 8893}],
        },
    ]


if __name__ == "__main__":
    # Leaving this to facilitate debugging.
    logging.basicConfig(
        format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG,
    )
    main()

from pathlib import Path
import shutil

root = Path(".")
ci = Path(__file__).resolve().parent

def copy_asset(name: str, target: str):
    src = ci / name
    dst = root / target
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)

copy_asset(
    "run53.HomeDashboard.kt",
    "app/src/main/java/ir/rahyar/app/core/home/HomeDashboard.kt"
)
copy_asset(
    "run53.PersonalPlacesStore.kt",
    "app/src/main/java/ir/rahyar/app/data/home/PersonalPlacesStore.kt"
)
copy_asset(
    "run53.HomeDashboardContractTest.kt",
    "app/src/test/java/ir/rahyar/app/core/home/HomeDashboardContractTest.kt"
)
copy_asset(
    "run53.HomeScreen.kt",
    "app/src/main/java/ir/rahyar/app/ui/screens/HomeScreen.kt"
)
copy_asset(
    "run53.HomeDashboardOverlay.kt",
    "app/src/main/java/ir/rahyar/app/ui/screens/HomeDashboardOverlay.kt"
)
copy_asset(
    "run53.PersianNumberFormatter.kt",
    "app/src/main/java/ir/rahyar/app/core/format/PersianNumberFormatter.kt"
)
copy_asset(
    "run53.PersianNumberFormatterTest.kt",
    "app/src/test/java/ir/rahyar/app/core/format/PersianNumberFormatterTest.kt"
)

nav_host = root / "app/src/main/java/ir/rahyar/app/navigation/RahyarNavHost.kt"
nh = nav_host.read_text()

if "import androidx.compose.foundation.layout.Box" not in nh:
    nh = nh.replace(
        "package ir.rahyar.app.navigation\n\n",
        "package ir.rahyar.app.navigation\n\n"
        "import androidx.compose.foundation.layout.Box\n"
        "import androidx.compose.ui.Alignment\n"
        "import androidx.compose.ui.Modifier\n",
        1
    )

if "import ir.rahyar.app.ui.screens.HomeDashboardOverlay" not in nh:
    nh = nh.replace(
        "import ir.rahyar.app.ui.screens.ActiveNavigationScreen\n",
        "import ir.rahyar.app.ui.screens.ActiveNavigationScreen\n"
        "import ir.rahyar.app.ui.screens.HomeDashboardOverlay\n",
        1
    )

home_start_marker = "        composable(Destinations.HOME) {\n"
home_end_marker = "        composable(Destinations.DESTINATION_SEARCH) {\n"
home_start = nh.find(home_start_marker)
home_end = nh.find(home_end_marker, home_start)
if home_start < 0 or home_end < 0:
    raise SystemExit("Run53 HOME destination block not found")

home_block = nh[home_start:home_end]
if "HomeDashboardOverlay(" not in home_block:
    home_lines = home_block.rstrip().splitlines()
    if len(home_lines) < 3 or home_lines[0].strip() != "composable(Destinations.HOME) {":
        raise SystemExit("Run53 unexpected HOME destination block")
    inner = ["    " + line for line in home_lines[1:-1]]
    overlay = [
        "            HomeDashboardOverlay(",
        "                navController = navController,",
        "                locationProvider = locationProvider,",
        "                navigationSession = navigationSession,",
        "                destinationSearchRepository = destinationSearchRepository,",
        "                weatherRepository = weatherRepository,",
        "                trafficRepository = trafficRepository,",
        "                modifier = Modifier.align(Alignment.BottomCenter)",
        "            )",
    ]
    rebuilt = [
        "        composable(Destinations.HOME) {",
        "            Box {",
        *inner,
        *overlay,
        "            }",
        "        }",
        "",
    ]
    nh = nh[:home_start] + "\n".join(rebuilt) + nh[home_end:]

nav_host.write_text(nh)

# Home dashboard needs persistent Trip Story read-back.
trip_store = root / "app/src/main/java/ir/rahyar/app/data/trip/TripStoryStore.kt"
ts = trip_store.read_text()
if "fun load(context: Context): List<TripStoryRecord>" not in ts:
    save_anchor = "    fun save(\n"
    save_pos = ts.find(save_anchor)
    if save_pos < 0:
        raise SystemExit("Run53 TripStoryStore save anchor missing")
    load_fn = """    fun load(context: Context): List<TripStoryRecord> {
        val prefs = context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val array = runCatching {
            JSONArray(prefs.getString(KEY_ITEMS, "[]") ?: "[]")
        }.getOrElse { JSONArray() }

        return buildList {
            for (index in 0 until array.length()) {
                array.optJSONObject(index)?.toRecord()?.let(::add)
            }
        }
    }

"""
    ts = ts[:save_pos] + load_fn + ts[save_pos:]

    helper_anchor = "    private fun TripStoryRecord.toJson(): JSONObject =\n"
    helper_pos = ts.find(helper_anchor)
    if helper_pos < 0:
        raise SystemExit("Run53 TripStoryStore toJson anchor missing")
    from_json = """    private fun JSONObject.toRecord(): TripStoryRecord? {
        val tripId = optString("tripId").trim()
        if (tripId.isBlank()) return null
        return TripStoryRecord(
            tripId = tripId,
            startedAtMillis = optLong("startedAtMillis", 0L),
            endedAtMillis = optLong("endedAtMillis", 0L),
            actualDistanceKm = optDouble("actualDistanceKm", 0.0),
            actualDurationMinutes = optInt("actualDurationMinutes", 0),
            averageSpeedKmh = optDouble("averageSpeedKmh", 0.0),
            maxSpeedKmh = optDouble("maxSpeedKmh", 0.0),
            rerouteCount = optInt("rerouteCount", 0),
            stopCount = optInt("stopCount", 0),
            mediaCount = optInt("mediaCount", 0),
            weatherEventCount = optInt("weatherEventCount", 0),
            trafficEventCount = optInt("trafficEventCount", 0),
            navigationRating = if (has("navigationRating") && !isNull("navigationRating")) {
                optInt("navigationRating")
            } else {
                null
            }
        )
    }

"""
    ts = ts[:helper_pos] + from_json + ts[helper_pos:]
    trip_store.write_text(ts)

theme = root / "app/src/main/java/ir/rahyar/app/ui/theme/Theme.kt"
t = theme.read_text()

if "import androidx.compose.runtime.CompositionLocalProvider" not in t:
    t = t.replace(
        "import androidx.compose.runtime.Composable\n",
        "import androidx.compose.runtime.Composable\n"
        "import androidx.compose.runtime.CompositionLocalProvider\n",
        1
    )
if "import androidx.compose.ui.platform.LocalLayoutDirection" not in t:
    t = t.replace(
        "import androidx.compose.ui.graphics.Color\n",
        "import androidx.compose.ui.graphics.Color\n"
        "import androidx.compose.ui.platform.LocalLayoutDirection\n"
        "import androidx.compose.ui.unit.LayoutDirection\n",
        1
    )

old_sig = """fun RahyarTheme(
    themeMode: RahyarThemeMode = RahyarThemeMode.SYSTEM,
    content: @Composable () -> Unit
) {"""
new_sig = """fun RahyarTheme(
    themeMode: RahyarThemeMode = RahyarThemeMode.SYSTEM,
    layoutDirection: LayoutDirection = LayoutDirection.Rtl,
    content: @Composable () -> Unit
) {"""
if old_sig not in t:
    raise SystemExit("Run53 RahyarTheme signature target missing")
t = t.replace(old_sig, new_sig, 1)

old_material = """    MaterialTheme(
        colorScheme = if (useDarkTheme) RahyarDarkColorScheme else RahyarLightColorScheme,
        typography = RahyarTypography,
        content = content
    )"""
new_material = """    CompositionLocalProvider(
        LocalLayoutDirection provides layoutDirection
    ) {
        MaterialTheme(
            colorScheme = if (useDarkTheme) RahyarDarkColorScheme else RahyarLightColorScheme,
            typography = RahyarTypography,
            content = content
        )
    }"""
if old_material not in t:
    raise SystemExit("Run53 MaterialTheme target missing")
t = t.replace(old_material, new_material, 1)
theme.write_text(t)

main = root / "app/src/main/java/ir/rahyar/app/MainActivity.kt"
m = main.read_text()
if "import androidx.compose.ui.unit.LayoutDirection" not in m:
    m = m.replace(
        "import androidx.compose.runtime.getValue\n",
        "import androidx.compose.runtime.getValue\n"
        "import androidx.compose.ui.unit.LayoutDirection\n",
        1
    )

theme_line = """            val themeValue by settingsRepository.themeModeFlow.collectAsStateWithLifecycle(initialValue = "system")"""
if theme_line not in m:
    raise SystemExit("Run53 theme flow anchor missing")
m = m.replace(
    theme_line,
    theme_line + """
            val languageValue by settingsRepository.languageFlow.collectAsStateWithLifecycle(initialValue = "fa")
            val layoutDirection = when (languageValue) {
                "fa", "ar", "ku" -> LayoutDirection.Rtl
                else -> LayoutDirection.Ltr
            }""",
    1
)

old_theme_call = "RahyarTheme(themeMode = themeMode) {"
new_theme_call = """RahyarTheme(
                themeMode = themeMode,
                layoutDirection = layoutDirection
            ) {"""
if old_theme_call not in m:
    raise SystemExit("Run53 RahyarTheme call target missing")
m = m.replace(old_theme_call, new_theme_call, 1)
main.write_text(m)

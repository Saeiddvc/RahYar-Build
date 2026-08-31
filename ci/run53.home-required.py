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

old_home_block = """        composable(Destinations.HOME) {
            RahyarMapScreen(
                locationProvider = locationProvider,
                navigationSession = navigationSession,
                routePreviewViewModel = routePreviewViewModel,
                settingsRepository = settingsRepository,
                providerManager = providerManager,
                searchViewModel = destinationSearchViewModel,
                onSettingsRequested = { navController.navigate(Destinations.SETTINGS) },
                onStartNavigation = { navController.navigate(Destinations.ACTIVE_NAVIGATION) }
            )
        }"""

new_home_block = """        composable(Destinations.HOME) {
            Box {
                RahyarMapScreen(
                    locationProvider = locationProvider,
                    navigationSession = navigationSession,
                    routePreviewViewModel = routePreviewViewModel,
                    settingsRepository = settingsRepository,
                    providerManager = providerManager,
                    searchViewModel = destinationSearchViewModel,
                    onSettingsRequested = { navController.navigate(Destinations.SETTINGS) },
                    onStartNavigation = { navController.navigate(Destinations.ACTIVE_NAVIGATION) }
                )
                HomeDashboardOverlay(
                    navController = navController,
                    locationProvider = locationProvider,
                    navigationSession = navigationSession,
                    destinationSearchRepository = destinationSearchRepository,
                    weatherRepository = weatherRepository,
                    trafficRepository = trafficRepository,
                    modifier = Modifier.align(Alignment.BottomCenter)
                )
            }
        }"""

if old_home_block not in nh:
    raise SystemExit("Run53 HOME route block target missing")

nh = nh.replace(old_home_block, new_home_block, 1)
nav_host.write_text(nh)

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

#!/usr/bin/env python3
from pathlib import Path


ROOT = Path("app/src")


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"Run58 contract file missing: {path}")
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Run58 field UX contract failed: {message}")


nav = read("main/java/ir/rahyar/app/navigation/RahyarNavHost.kt")
home = read("main/java/ir/rahyar/app/ui/screens/HomeDashboardOverlay.kt")
map_screen = read("main/java/ir/rahyar/app/ui/screens/RahyarMapScreen.kt")
map_view = read("main/java/ir/rahyar/app/core/map/RahyarMapView.kt")
session = read("main/java/ir/rahyar/app/navigation/NavigationSession.kt")
preview_vm = read("main/java/ir/rahyar/app/ui/navigation/RoutePreviewViewModel.kt")
settings = read("main/java/ir/rahyar/app/ui/settings/SettingsScreen.kt")
pre_navigation = read("main/java/ir/rahyar/app/ui/components/PreNavigationComponents.kt")
active = read("main/java/ir/rahyar/app/ui/screens/ActiveNavigationScreen.kt")
controls = read("main/java/ir/rahyar/app/ui/components/NavigationControls.kt")
activity = read("main/java/ir/rahyar/app/MainActivity.kt")
waypoint_tests = read("test/java/ir/rahyar/app/navigation/NavigationSessionWaypointTest.kt")

require("BottomSheetScaffold(" in nav, "home tools are not hosted in a draggable bottom sheet")
require("sheetPeekHeight = if (showHomeSheet) 104.dp else 0.dp" in nav, "collapsed search-only peek height is missing")
require("homeSearchRequestToken++" in nav and "searchRequestToken = homeSearchRequestToken" in nav, "single search flow is not wired")
require("navigationSession.beginNavigation(route)" in nav, "navigation session is not started before screen transition")
require(home.count('"کجا می‌خواهید بروید؟"') == 1, "home sheet must expose exactly one search action")
require('"کجا می‌خواهید بروید؟"' not in map_screen, "duplicate map-header search action remains")
require("navController.navigate(Destinations.DESTINATION_SEARCH)" not in home, "legacy second search flow remains in the home sheet")

require("navigationSession.addStop(" in map_screen, "waypoint selection does not update the itinerary")
require("val refreshed = navigationSession.state.value" in map_screen, "waypoint recalculation uses stale session state")
require("waypoints = confirmed.waypoints" in map_screen, "destination confirmation can reuse stale waypoints")
require("_uiState.value = RoutePreviewUiState.Loading" in preview_vm, "route preview does not invalidate the stale route immediately")
require("waypoints.distinct().take(8)" in session, "waypoint normalization/cap is missing")
require("it.id == id || it.location == location" in session, "duplicate stops are not rejected")
require("duplicateStopSelectionIsIdempotent" in waypoint_tests, "duplicate-stop regression test is missing")
require("itineraryNeverAcceptsMoreThanEightPendingStops" in waypoint_tests, "waypoint-cap regression test is missing")

require("lifecycleOwner.lifecycle.currentState.isAtLeast" in map_view, "MapView does not catch up to the current lifecycle")
require("rememberUpdatedState(onMapReady)" in map_view, "MapView retains a stale ready callback")
require("MapLatLng(35.7219, 51.3347)" in map_screen, "safe Iran-area initial camera is missing")
require("recenterRequestToken" in map_screen and "Icons.Default.MyLocation" in map_screen, "working recenter control is missing")

require("TransportMode.entries.filter(providerManager::isRoutingSupported)" in settings, "settings still lists unsupported travel modes")
for unavailable in ("Android Auto", "نقشه‌های آفلاین", 'Section("زبان")', 'Section("واحد سرعت")'):
    require(unavailable not in settings, f"non-functional settings item remains: {unavailable}")
for unavailable in ("پرهیز از محدوده آلودگی", "پرهیز از عوارضی", "راهنمای صوتی در این نسخه فعال نیست"):
    require(unavailable not in pre_navigation, f"non-functional pre-navigation item remains: {unavailable}")
for unavailable in ("نمایش ترافیک", "بازمسیر‌یابی در ترافیک سنگین", "بازمسیر‌یابی در آب‌وهوای شدید"):
    require(unavailable not in active, f"non-functional quick setting remains: {unavailable}")
require("if (alternativesEnabled)" in controls and "if (voiceAvailable)" in controls, "unavailable navigation controls are still rendered disabled")
require("popBackStack(route = Destinations.HOME" in active, "invalid navigation state can still strand the user on a blank screen")
require("layoutDirection = LayoutDirection.Rtl" in activity and "languageValue" not in activity, "persisted unsupported language can still break RTL")

gradle = Path("app/build.gradle.kts").read_text(encoding="utf-8")
require("versionCode = 36" in gradle, "Run58 versionCode must be 36")
require('versionName = "1.7.4-run58-field-fixes"' in gradle, "Run58 versionName mismatch")

print("Run58 field UX contract passed: single search sheet, stable map, waypoint integrity, active-only settings, and blank-screen recovery.")

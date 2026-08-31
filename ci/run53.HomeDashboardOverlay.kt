package ir.rahyar.app.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.LocalGasStation
import androidx.compose.material.icons.filled.LocalHospital
import androidx.compose.material.icons.filled.LocalParking
import androidx.compose.material.icons.filled.Restaurant
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Work
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavHostController
import ir.rahyar.app.core.home.HomeServiceShortcut
import ir.rahyar.app.core.home.filterHomeServiceResults
import ir.rahyar.app.core.home.requiredHomeServiceShortcuts
import ir.rahyar.app.core.home.trafficStatusLabel
import ir.rahyar.app.core.home.weatherStatusLabel
import ir.rahyar.app.core.location.LocationProvider
import ir.rahyar.app.data.home.PersonalPlacesStore
import ir.rahyar.app.data.home.StoredPersonalPlace
import ir.rahyar.app.data.trip.TripStoryRecord
import ir.rahyar.app.data.trip.TripStoryStore
import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.Route
import ir.rahyar.app.domain.models.RouteType
import ir.rahyar.app.domain.models.SearchResult
import ir.rahyar.app.domain.models.TransportMode
import ir.rahyar.app.domain.repository.DestinationSearchRepository
import ir.rahyar.app.domain.repository.TrafficRepository
import ir.rahyar.app.domain.repository.WeatherRepository
import ir.rahyar.app.navigation.Destinations
import ir.rahyar.app.navigation.NavigationSession
import kotlinx.coroutines.launch
import java.time.LocalDateTime

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeDashboardOverlay(
    navController: NavHostController,
    locationProvider: LocationProvider,
    navigationSession: NavigationSession,
    destinationSearchRepository: DestinationSearchRepository,
    weatherRepository: WeatherRepository,
    trafficRepository: TrafficRepository,
    modifier: Modifier = Modifier
) {
    val session by navigationSession.state.collectAsStateWithLifecycle()
    if (session.destination != null || session.selectedRoute != null) return

    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var currentLocation by remember { mutableStateOf<LatLng?>(session.origin) }
    var homePlace by remember { mutableStateOf(PersonalPlacesStore.home(context)) }
    var workPlace by remember { mutableStateOf(PersonalPlacesStore.work(context)) }
    var savedPlaces by remember { mutableStateOf(PersonalPlacesStore.savedPlaces(context)) }
    var recentDestinations by remember { mutableStateOf<List<SearchResult>>(emptyList()) }
    var savedTrips by remember { mutableStateOf<List<TripStoryRecord>>(TripStoryStore.load(context)) }
    var weatherStatus by remember { mutableStateOf("آب‌وهوا: در حال دریافت") }
    var trafficStatus by remember { mutableStateOf("ترافیک: در حال دریافت") }
    var serviceTitle by remember { mutableStateOf<String?>(null) }
    var serviceResults by remember { mutableStateOf<List<SearchResult>>(emptyList()) }
    var serviceLoading by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("آماده برای همراهی") }

    fun hasPermission(): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    var permissionGranted by remember { mutableStateOf(hasPermission()) }

    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        permissionGranted =
            result[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
                result[Manifest.permission.ACCESS_COARSE_LOCATION] == true
    }

    suspend fun refreshOrigin(): LatLng? {
        if (!permissionGranted) return currentLocation
        val loc = runCatching { locationProvider.getLastLocation() }.getOrNull() ?: return currentLocation
        val point = LatLng(loc.latitude, loc.longitude)
        currentLocation = point
        navigationSession.setOrigin(point)
        return point
    }

    fun goToDestination(result: SearchResult) {
        scope.launch {
            refreshOrigin()
            destinationSearchRepository.saveRecent(result)
            recentDestinations = destinationSearchRepository.recentDestinations()
            navigationSession.setDestinationCandidate(result)
            navController.navigate(Destinations.CONFIRM_DESTINATION) {
                launchSingleTop = true
            }
        }
    }

    fun goToPersonal(place: StoredPersonalPlace) {
        goToDestination(
            SearchResult(
                id = "personal-" + place.id,
                title = place.label,
                subtitle = "مکان شخصی ذخیره‌شده",
                location = place.location
            )
        )
    }

    fun runServiceSearch(spec: HomeServiceShortcut) {
        scope.launch {
            serviceTitle = spec.label
            serviceLoading = true
            val origin = refreshOrigin()
            val raw = runCatching { destinationSearchRepository.search(spec.query) }.getOrDefault(emptyList())
            serviceResults = filterHomeServiceResults(raw, origin)
            serviceLoading = false
            if (serviceResults.isEmpty()) {
                status = "نتیجه محلی معتبر برای «" + spec.label + "» پیدا نشد"
            }
        }
    }

    LaunchedEffect(Unit) {
        if (!permissionGranted) {
            launcher.launch(
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION
                )
            )
        }
        recentDestinations = runCatching {
            destinationSearchRepository.recentDestinations()
        }.getOrDefault(emptyList())
        savedTrips = TripStoryStore.load(context)
        refreshOrigin()
    }

    LaunchedEffect(currentLocation) {
        val point = currentLocation ?: return@LaunchedEffect
        val route = localStatusQueryRoute(point)
        weatherStatus = weatherStatusLabel(
            runCatching { weatherRepository.getWeatherAlongRoute(route) }.getOrNull()
        )
        trafficStatus = trafficStatusLabel(
            runCatching { trafficRepository.getTrafficForRoute(route) }.getOrNull()
        )
    }

    Surface(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(max = 430.dp)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        shape = RoundedCornerShape(22.dp),
        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.97f),
        tonalElevation = 4.dp
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(14.dp)
        ) {
            Button(
                modifier = Modifier.fillMaxWidth(),
                onClick = { navController.navigate(Destinations.DESTINATION_SEARCH) }
            ) {
                Icon(Icons.Default.Search, contentDescription = null)
                Spacer(Modifier.padding(4.dp))
                Text("کجا می‌خواهید بروید؟")
            }

            Spacer(Modifier.height(8.dp))
            Text(weatherStatus, style = MaterialTheme.typography.bodySmall)
            Text(trafficStatus, style = MaterialTheme.typography.bodySmall)

            Spacer(Modifier.height(10.dp))
            Text("مکان‌های شخصی", style = MaterialTheme.typography.titleSmall)
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                DashboardShortcut(
                    label = if (homePlace == null) "ثبت خانه" else "خانه",
                    icon = Icons.Default.Home,
                    modifier = Modifier.weight(1f)
                ) {
                    val place = homePlace
                    if (place != null) {
                        goToPersonal(place)
                    } else {
                        scope.launch {
                            val point = refreshOrigin()
                            if (point != null) {
                                PersonalPlacesStore.saveHome(context, point)
                                homePlace = PersonalPlacesStore.home(context)
                            }
                        }
                    }
                }

                DashboardShortcut(
                    label = if (workPlace == null) "ثبت کار" else "محل کار",
                    icon = Icons.Default.Work,
                    modifier = Modifier.weight(1f)
                ) {
                    val place = workPlace
                    if (place != null) {
                        goToPersonal(place)
                    } else {
                        scope.launch {
                            val point = refreshOrigin()
                            if (point != null) {
                                PersonalPlacesStore.saveWork(context, point)
                                workPlace = PersonalPlacesStore.work(context)
                            }
                        }
                    }
                }

                DashboardShortcut(
                    label = "ذخیره فعلی",
                    icon = Icons.Default.Bookmark,
                    modifier = Modifier.weight(1f)
                ) {
                    scope.launch {
                        val point = refreshOrigin()
                        if (point != null) {
                            PersonalPlacesStore.addSaved(
                                context = context,
                                label = "مکان ذخیره‌شده " + (savedPlaces.size + 1),
                                location = point
                            )
                            savedPlaces = PersonalPlacesStore.savedPlaces(context)
                        }
                    }
                }
            }

            if (savedPlaces.isNotEmpty()) {
                savedPlaces.take(3).forEach { place ->
                    DashboardListItem(
                        title = place.label,
                        subtitle = "مکان ذخیره‌شده",
                        onClick = { goToPersonal(place) }
                    )
                }
            }

            Spacer(Modifier.height(10.dp))
            Text("خدمات نزدیک", style = MaterialTheme.typography.titleSmall)
            requiredHomeServiceShortcuts.chunked(2).forEach { rowItems ->
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    rowItems.forEach { spec ->
                        DashboardShortcut(
                            label = spec.label,
                            icon = dashboardServiceIcon(spec.label),
                            modifier = Modifier.weight(1f),
                            onClick = { runServiceSearch(spec) }
                        )
                    }
                    if (rowItems.size == 1) Spacer(Modifier.weight(1f))
                }
                Spacer(Modifier.height(5.dp))
            }

            if (recentDestinations.isNotEmpty()) {
                Text("مقصدهای اخیر", style = MaterialTheme.typography.titleSmall)
                recentDestinations.take(3).forEach { item ->
                    DashboardListItem(
                        title = item.title,
                        subtitle = item.subtitle ?: "مقصد اخیر",
                        onClick = { goToDestination(item) }
                    )
                }
            }

            Text("سفرهای ذخیره‌شده", style = MaterialTheme.typography.titleSmall)
            if (savedTrips.isEmpty()) {
                Text(
                    "هنوز سفر واقعی ذخیره‌شده‌ای وجود ندارد.",
                    style = MaterialTheme.typography.bodySmall
                )
            } else {
                savedTrips.take(2).forEach { trip ->
                    DashboardListItem(
                        title = "سفر واقعی • " + String.format(java.util.Locale.US, "%.1f", trip.actualDistanceKm).replace('.', '٫') + " کیلومتر",
                        subtitle = trip.actualDurationMinutes.toString() + " دقیقه • " + trip.stopCount + " توقف",
                        onClick = { status = "این سفر از TripTrace واقعی ذخیره شده است" }
                    )
                }
            }

            Text(
                status,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }

    if (serviceTitle != null) {
        ModalBottomSheet(
            onDismissRequest = {
                serviceTitle = null
                serviceResults = emptyList()
            }
        ) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .navigationBarsPadding()
                    .padding(18.dp)
            ) {
                Text(
                    "نتایج نزدیک: " + serviceTitle.orEmpty(),
                    style = MaterialTheme.typography.titleLarge
                )
                if (serviceLoading) {
                    LinearProgressIndicator(Modifier.fillMaxWidth())
                } else if (serviceResults.isEmpty()) {
                    Text("نتیجه محلی معتبر پیدا نشد.")
                } else {
                    serviceResults.forEach { result ->
                        DashboardListItem(
                            title = result.title,
                            subtitle = result.subtitle ?: "نتیجه نزدیک",
                            onClick = {
                                serviceTitle = null
                                serviceResults = emptyList()
                                goToDestination(result)
                            }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun DashboardShortcut(
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    OutlinedButton(
        modifier = modifier.heightIn(min = 44.dp),
        onClick = onClick,
        contentPadding = PaddingValues(horizontal = 6.dp, vertical = 6.dp)
    ) {
        Icon(icon, contentDescription = null)
        Spacer(Modifier.padding(3.dp))
        Text(label, style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
private fun DashboardListItem(
    title: String,
    subtitle: String,
    onClick: () -> Unit
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp)
            .clickable(onClick = onClick),
        tonalElevation = 1.dp
    ) {
        Column(Modifier.padding(horizontal = 10.dp, vertical = 7.dp)) {
            Text(title, style = MaterialTheme.typography.bodyMedium)
            Text(
                subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

private fun dashboardServiceIcon(
    label: String
): androidx.compose.ui.graphics.vector.ImageVector =
    when {
        "سوخت" in label -> Icons.Default.LocalGasStation
        "غذا" in label || "کافه" in label -> Icons.Default.Restaurant
        "پارکینگ" in label -> Icons.Default.LocalParking
        "بیمارستان" in label -> Icons.Default.LocalHospital
        "مجتمع" in label -> Icons.Default.Home
        else -> Icons.Default.Bookmark
    }

private fun localStatusQueryRoute(point: LatLng): Route =
    Route(
        id = "home-dashboard-status",
        type = RouteType.RECOMMENDED,
        points = listOf(point, LatLng(point.latitude, point.longitude + 0.01)),
        durationMinutes = 2,
        distanceKm = 1.0,
        eta = LocalDateTime.now(),
        transportMode = TransportMode.CAR
    )

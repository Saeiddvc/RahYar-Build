package ir.rahyar.app.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
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
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.navigation.NavHostController
import ir.rahyar.app.R
import ir.rahyar.app.core.home.HomeServiceShortcut
import ir.rahyar.app.core.home.filterHomeServiceResults
import ir.rahyar.app.core.home.requiredHomeServiceShortcuts
import ir.rahyar.app.core.home.trafficStatusLabel
import ir.rahyar.app.core.home.weatherStatusLabel
import ir.rahyar.app.core.location.LocationProvider
import ir.rahyar.app.core.map.RahyarMapView
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
import org.maplibre.android.annotations.Marker
import org.maplibre.android.annotations.MarkerOptions
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng as MapLatLng
import org.maplibre.android.maps.MapLibreMap
import java.time.LocalDateTime

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    navController: NavHostController,
    locationProvider: LocationProvider,
    navigationSession: NavigationSession,
    destinationSearchRepository: DestinationSearchRepository,
    weatherRepository: WeatherRepository,
    trafficRepository: TrafficRepository
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var mapRef by remember { mutableStateOf<MapLibreMap?>(null) }
    var currentMarker by remember { mutableStateOf<Marker?>(null) }
    var currentLocation by remember { mutableStateOf<LatLng?>(null) }
    var status by remember {
        mutableStateOf("مقصد را جستجو کنید یا یکی از میان‌برهای هوشمند را انتخاب کنید")
    }

    var homePlace by remember {
        mutableStateOf(PersonalPlacesStore.home(context))
    }
    var workPlace by remember {
        mutableStateOf(PersonalPlacesStore.work(context))
    }
    var savedPlaces by remember {
        mutableStateOf(PersonalPlacesStore.savedPlaces(context))
    }
    var recentDestinations by remember {
        mutableStateOf<List<SearchResult>>(emptyList())
    }
    var savedTrips by remember {
        mutableStateOf<List<TripStoryRecord>>(TripStoryStore.load(context))
    }

    var weatherStatus by remember {
        mutableStateOf("آب‌وهوا: در حال دریافت")
    }
    var trafficStatus by remember {
        mutableStateOf("ترافیک: در حال دریافت")
    }

    var serviceTitle by remember { mutableStateOf<String?>(null) }
    var serviceResults by remember {
        mutableStateOf<List<SearchResult>>(emptyList())
    }
    var serviceLoading by remember { mutableStateOf(false) }

    fun hasPermission(): Boolean =
        ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.ACCESS_COARSE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED

    var permissionGranted by remember {
        mutableStateOf(hasPermission())
    }

    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        permissionGranted =
            result[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
                result[Manifest.permission.ACCESS_COARSE_LOCATION] == true
    }

    suspend fun refreshOrigin(): LatLng? {
        if (!permissionGranted) return currentLocation
        val loc = runCatching {
            locationProvider.getLastLocation()
        }.getOrNull() ?: return currentLocation

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
            serviceLoading = true
            serviceTitle = spec.label
            val origin = refreshOrigin()
            val raw = runCatching {
                destinationSearchRepository.search(spec.query)
            }.getOrDefault(emptyList())
            serviceResults = filterHomeServiceResults(
                results = raw,
                currentLocation = origin
            )
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
    }

    LaunchedEffect(permissionGranted, mapRef) {
        val map = mapRef ?: return@LaunchedEffect
        if (!permissionGranted) return@LaunchedEffect
        val point = refreshOrigin() ?: return@LaunchedEffect

        currentMarker?.let {
            runCatching { map.removeMarker(it) }
        }
        currentMarker = map.addMarker(
            MarkerOptions()
                .position(MapLatLng(point.latitude, point.longitude))
                .title("موقعیت فعلی")
        )
        map.animateCamera(
            CameraUpdateFactory.newLatLngZoom(
                MapLatLng(point.latitude, point.longitude),
                15.0
            )
        )
        status = "موقعیت فعلی با موفقیت دریافت شد"
    }

    LaunchedEffect(currentLocation) {
        val point = currentLocation ?: return@LaunchedEffect
        val queryRoute = localStatusQueryRoute(point)

        val weather = runCatching {
            weatherRepository.getWeatherAlongRoute(queryRoute)
        }.getOrNull()
        weatherStatus = weatherStatusLabel(weather)

        val traffic = runCatching {
            trafficRepository.getTrafficForRoute(queryRoute)
        }.getOrNull()
        trafficStatus = trafficStatusLabel(traffic)
    }

    Box(
        Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        RahyarMapView(Modifier.fillMaxSize()) { map ->
            mapRef = map
            if (!permissionGranted) {
                map.animateCamera(
                    CameraUpdateFactory.newLatLngZoom(
                        MapLatLng(35.7219, 51.3347),
                        11.0
                    )
                )
            }
            map.addOnMapClickListener { tapped ->
                val selected = LatLng(tapped.latitude, tapped.longitude)
                goToDestination(
                    SearchResult(
                        id = "map-tap-" +
                            selected.latitude + "-" +
                            selected.longitude,
                        title = "نقطه روی نقشه",
                        subtitle = null,
                        location = selected
                    )
                )
                true
            }
        }

        Surface(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .fillMaxWidth()
                .fillMaxHeight(0.82f)
                .padding(12.dp),
            shape = RoundedCornerShape(22.dp),
            color = MaterialTheme.colorScheme.surface.copy(alpha = 0.96f),
            tonalElevation = 4.dp
        ) {
            Column(
                Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(14.dp)
            ) {
                Row(
                    Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        painter = painterResource(R.drawable.ic_rahyar_mark),
                        contentDescription = "نشان راه‌یار",
                        tint = androidx.compose.ui.graphics.Color.Unspecified,
                        modifier = Modifier.size(42.dp)
                    )
                    Spacer(Modifier.width(10.dp))
                    Column(Modifier.weight(1f)) {
                        Text(
                            "راه‌یار",
                            style = MaterialTheme.typography.headlineMedium,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Text(
                            "همراه هوشمند شما در سفر",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Spacer(Modifier.height(10.dp))

                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp)
                        .clickable {
                            scope.launch {
                                refreshOrigin()
                                navController.navigate(
                                    Destinations.DESTINATION_SEARCH
                                )
                            }
                        },
                    shape = RoundedCornerShape(18.dp),
                    tonalElevation = 2.dp
                ) {
                    Row(
                        Modifier
                            .fillMaxSize()
                            .padding(horizontal = 16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            Icons.Default.Search,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary
                        )
                        Spacer(Modifier.width(12.dp))
                        Text(
                            "کجا می‌خواهید بروید؟",
                            style = MaterialTheme.typography.bodyLarge
                        )
                    }
                }

                Spacer(Modifier.height(10.dp))
                Text(
                    "وضعیت مسیر",
                    style = MaterialTheme.typography.titleSmall
                )
                StatusCard(weatherStatus)
                Spacer(Modifier.height(4.dp))
                StatusCard(trafficStatus)

                Spacer(Modifier.height(12.dp))
                Text(
                    "مکان‌های شخصی",
                    style = MaterialTheme.typography.titleSmall
                )
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    PersonalShortcut(
                        label = if (homePlace == null) "ثبت خانه" else "خانه",
                        icon = Icons.Default.Home,
                        modifier = Modifier.weight(1f)
                    ) {
                        val existing = homePlace
                        if (existing != null) {
                            goToPersonal(existing)
                        } else {
                            scope.launch {
                                val point = refreshOrigin()
                                if (point != null) {
                                    PersonalPlacesStore.saveHome(context, point)
                                    homePlace = PersonalPlacesStore.home(context)
                                    status = "خانه از موقعیت فعلی ذخیره شد"
                                } else {
                                    status = "برای ثبت خانه، موقعیت مکانی لازم است"
                                }
                            }
                        }
                    }

                    PersonalShortcut(
                        label = if (workPlace == null) "ثبت کار" else "محل کار",
                        icon = Icons.Default.Work,
                        modifier = Modifier.weight(1f)
                    ) {
                        val existing = workPlace
                        if (existing != null) {
                            goToPersonal(existing)
                        } else {
                            scope.launch {
                                val point = refreshOrigin()
                                if (point != null) {
                                    PersonalPlacesStore.saveWork(context, point)
                                    workPlace = PersonalPlacesStore.work(context)
                                    status = "محل کار از موقعیت فعلی ذخیره شد"
                                } else {
                                    status = "برای ثبت محل کار، موقعیت مکانی لازم است"
                                }
                            }
                        }
                    }

                    PersonalShortcut(
                        label = "ذخیره فعلی",
                        icon = Icons.Default.Bookmark,
                        modifier = Modifier.weight(1f)
                    ) {
                        scope.launch {
                            val point = refreshOrigin()
                            if (point != null) {
                                PersonalPlacesStore.addSaved(
                                    context = context,
                                    label = "مکان ذخیره‌شده " +
                                        toPersianDigits(
                                            (savedPlaces.size + 1).toString()
                                        ),
                                    location = point
                                )
                                savedPlaces =
                                    PersonalPlacesStore.savedPlaces(context)
                                status = "موقعیت فعلی ذخیره شد"
                            }
                        }
                    }
                }

                if (savedPlaces.isNotEmpty()) {
                    Spacer(Modifier.height(6.dp))
                    savedPlaces.take(4).forEach { place ->
                        HomeListItem(
                            title = place.label,
                            subtitle = "مکان ذخیره‌شده",
                            onClick = { goToPersonal(place) }
                        )
                    }
                }

                Spacer(Modifier.height(12.dp))
                Text(
                    "خدمات نزدیک",
                    style = MaterialTheme.typography.titleSmall
                )

                requiredHomeServiceShortcuts
                    .chunked(2)
                    .forEach { rowItems ->
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement =
                                Arrangement.spacedBy(8.dp)
                        ) {
                            rowItems.forEach { spec ->
                                ServiceShortcut(
                                    label = spec.label,
                                    icon = serviceIcon(spec.label),
                                    modifier = Modifier.weight(1f),
                                    onClick = { runServiceSearch(spec) }
                                )
                            }
                            if (rowItems.size == 1) {
                                Spacer(Modifier.weight(1f))
                            }
                        }
                        Spacer(Modifier.height(6.dp))
                    }

                if (recentDestinations.isNotEmpty()) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "مقصدهای اخیر",
                        style = MaterialTheme.typography.titleSmall
                    )
                    recentDestinations.take(4).forEach { item ->
                        HomeListItem(
                            title = item.title,
                            subtitle = item.subtitle ?: "مقصد اخیر",
                            onClick = { goToDestination(item) }
                        )
                    }
                }

                Spacer(Modifier.height(8.dp))
                Text(
                    "سفرهای ذخیره‌شده",
                    style = MaterialTheme.typography.titleSmall
                )
                if (savedTrips.isEmpty()) {
                    Text(
                        "هنوز سفر واقعی ذخیره‌شده‌ای وجود ندارد.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    savedTrips.take(3).forEach { trip ->
                        HomeListItem(
                            title = "سفر واقعی • " +
                                toPersianDigits(
                                    "%.1f".format(
                                        java.util.Locale.US,
                                        trip.actualDistanceKm
                                    ).replace('.', '٫')
                                ) +
                                " کیلومتر",
                            subtitle = toPersianDigits(
                                trip.actualDurationMinutes.toString()
                            ) + " دقیقه • " +
                                toPersianDigits(
                                    trip.stopCount.toString()
                                ) + " توقف",
                            onClick = {
                                status =
                                    "این سفر از TripTrace واقعی ذخیره شده است"
                            }
                        )
                    }
                }

                Spacer(Modifier.height(8.dp))
                Text(
                    status,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(70.dp))
            }
        }

        FloatingActionButton(
            onClick = {
                navController.navigate(Destinations.SETTINGS)
            },
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(20.dp)
        ) {
            Text("تنظیم")
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
                Spacer(Modifier.height(8.dp))
                if (serviceLoading) {
                    LinearProgressIndicator(
                        modifier = Modifier.fillMaxWidth()
                    )
                } else if (serviceResults.isEmpty()) {
                    Text(
                        "نتیجه محلی معتبر پیدا نشد.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                } else {
                    serviceResults.forEach { result ->
                        HomeListItem(
                            title = result.title,
                            subtitle =
                                result.subtitle ?: "نتیجه نزدیک",
                            onClick = {
                                serviceTitle = null
                                serviceResults = emptyList()
                                goToDestination(result)
                            }
                        )
                    }
                }
                Spacer(Modifier.height(14.dp))
            }
        }
    }
}

@Composable
private fun StatusCard(text: String) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surfaceVariant
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.padding(
                horizontal = 12.dp,
                vertical = 8.dp
            )
        )
    }
}

@Composable
private fun PersonalShortcut(
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    OutlinedButton(
        modifier = modifier,
        onClick = onClick,
        contentPadding = PaddingValues(
            horizontal = 4.dp,
            vertical = 7.dp
        )
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                icon,
                contentDescription = label,
                modifier = Modifier.size(20.dp)
            )
            Text(
                label,
                style = MaterialTheme.typography.labelSmall,
                maxLines = 1
            )
        }
    }
}

@Composable
private fun ServiceShortcut(
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    OutlinedButton(
        modifier = modifier.heightIn(min = 48.dp),
        onClick = onClick,
        contentPadding = PaddingValues(
            horizontal = 6.dp,
            vertical = 6.dp
        )
    ) {
        Icon(
            icon,
            contentDescription = null,
            modifier = Modifier.size(18.dp)
        )
        Spacer(Modifier.width(5.dp))
        Text(
            label,
            style = MaterialTheme.typography.labelSmall,
            maxLines = 2
        )
    }
}

@Composable
private fun HomeListItem(
    title: String,
    subtitle: String,
    onClick: () -> Unit
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 3.dp)
            .clip(RoundedCornerShape(12.dp))
            .clickable(onClick = onClick),
        tonalElevation = 1.dp
    ) {
        Column(
            Modifier.padding(
                horizontal = 12.dp,
                vertical = 8.dp
            )
        ) {
            Text(
                title,
                style = MaterialTheme.typography.bodyMedium
            )
            Text(
                subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2
            )
        }
    }
}

private fun serviceIcon(
    label: String
): androidx.compose.ui.graphics.vector.ImageVector =
    when {
        "سوخت" in label -> Icons.Default.LocalGasStation
        "غذا" in label || "کافه" in label -> Icons.Default.Restaurant
        "پارکینگ" in label -> Icons.Default.LocalParking
        "بیمارستان" in label -> Icons.Default.LocalHospital
        "مجتمع" in label -> Icons.Default.Home
        "بهداشتی" in label -> Icons.Default.Search
        else -> Icons.Default.Bookmark
    }

private fun localStatusQueryRoute(
    point: LatLng
): Route =
    Route(
        id = "home-local-status",
        type = RouteType.RECOMMENDED,
        points = listOf(
            point,
            LatLng(
                point.latitude,
                point.longitude + 0.01
            )
        ),
        durationMinutes = 2,
        distanceKm = 1.0,
        eta = LocalDateTime.now(),
        transportMode = TransportMode.CAR
    )

private fun toPersianDigits(value: String): String =
    value
        .replace('0', '۰')
        .replace('1', '۱')
        .replace('2', '۲')
        .replace('3', '۳')
        .replace('4', '۴')
        .replace('5', '۵')
        .replace('6', '۶')
        .replace('7', '۷')
        .replace('8', '۸')
        .replace('9', '۹')

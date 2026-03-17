// mobile/lib/models/city.dart
// Urban Intelligence Framework v2.0.0
// City data model

class City {
  final String cityId;
  final String name;
  final String country;
  final double latitude;
  final double longitude;
  final String currency;
  final bool isCached;
  final int? listingCount;

  const City({
    required this.cityId,
    required this.name,
    required this.country,
    required this.latitude,
    required this.longitude,
    required this.currency,
    required this.isCached,
    this.listingCount,
  });

  factory City.fromJson(Map<String, dynamic> json) => City(
        cityId: json['city_id'] as String,
        name: json['name'] as String,
        country: json['country'] as String,
        latitude: (json['latitude'] as num).toDouble(),
        longitude: (json['longitude'] as num).toDouble(),
        currency: json['currency'] as String,
        isCached: json['is_cached'] as bool,
        listingCount: json['listing_count'] as int?,
      );

  Map<String, dynamic> toJson() => {
        'city_id': cityId,
        'name': name,
        'country': country,
        'latitude': latitude,
        'longitude': longitude,
        'currency': currency,
        'is_cached': isCached,
        'listing_count': listingCount,
      };
}

// mobile/lib/models/prediction.dart
// Urban Intelligence Framework v2.0.0
// Prediction request and result data models

class PredictionRequest {
  final String cityId;
  final String roomType;
  final String? propertyType;
  final String? neighbourhood;
  final int accommodates;
  final int bedrooms;
  final int beds;
  final double bathrooms;
  final int amenityCount;
  final double reviewScoresRating;
  final int numberOfReviews;
  final int availability365;
  final int minimumNights;
  final bool hostIsSuperhost;
  final bool instantBookable;
  final double latitude;
  final double longitude;

  const PredictionRequest({
    required this.cityId,
    required this.roomType,
    this.propertyType = 'Apartment',
    this.neighbourhood = 'unknown',
    required this.accommodates,
    required this.bedrooms,
    required this.beds,
    required this.bathrooms,
    required this.amenityCount,
    required this.reviewScoresRating,
    required this.numberOfReviews,
    required this.availability365,
    required this.minimumNights,
    required this.hostIsSuperhost,
    required this.instantBookable,
    required this.latitude,
    required this.longitude,
  });

  Map<String, dynamic> toJson() => {
        'city_id': cityId,
        'room_type': roomType,
        'property_type': propertyType,
        'neighbourhood': neighbourhood,
        'accommodates': accommodates,
        'bedrooms': bedrooms,
        'beds': beds,
        'bathrooms': bathrooms,
        'amenity_count': amenityCount,
        'review_scores_rating': reviewScoresRating,
        'number_of_reviews': numberOfReviews,
        'availability_365': availability365,
        'minimum_nights': minimumNights,
        'host_is_superhost': hostIsSuperhost,
        'instant_bookable': instantBookable,
        'latitude': latitude,
        'longitude': longitude,
      };

  PredictionRequest copyWith({
    String? cityId,
    String? roomType,
    String? propertyType,
    String? neighbourhood,
    int? accommodates,
    int? bedrooms,
    int? beds,
    double? bathrooms,
    int? amenityCount,
    double? reviewScoresRating,
    int? numberOfReviews,
    int? availability365,
    int? minimumNights,
    bool? hostIsSuperhost,
    bool? instantBookable,
    double? latitude,
    double? longitude,
  }) =>
      PredictionRequest(
        cityId: cityId ?? this.cityId,
        roomType: roomType ?? this.roomType,
        propertyType: propertyType ?? this.propertyType,
        neighbourhood: neighbourhood ?? this.neighbourhood,
        accommodates: accommodates ?? this.accommodates,
        bedrooms: bedrooms ?? this.bedrooms,
        beds: beds ?? this.beds,
        bathrooms: bathrooms ?? this.bathrooms,
        amenityCount: amenityCount ?? this.amenityCount,
        reviewScoresRating: reviewScoresRating ?? this.reviewScoresRating,
        numberOfReviews: numberOfReviews ?? this.numberOfReviews,
        availability365: availability365 ?? this.availability365,
        minimumNights: minimumNights ?? this.minimumNights,
        hostIsSuperhost: hostIsSuperhost ?? this.hostIsSuperhost,
        instantBookable: instantBookable ?? this.instantBookable,
        latitude: latitude ?? this.latitude,
        longitude: longitude ?? this.longitude,
      );
}

// ── Result ────────────────────────────────────────────────────────────────

class ConfidenceInterval {
  final double lower;
  final double upper;
  const ConfidenceInterval({required this.lower, required this.upper});

  factory ConfidenceInterval.fromJson(Map<String, dynamic> json) =>
      ConfidenceInterval(
        lower: (json['lower'] as num).toDouble(),
        upper: (json['upper'] as num).toDouble(),
      );

  double get range => upper - lower;
}

class PredictionResult {
  final String predictionId;
  final String cityId;
  final double predictedPrice;
  final String currency;
  final ConfidenceInterval confidenceInterval;
  final double latencyMs;
  final String modelVersion;

  const PredictionResult({
    required this.predictionId,
    required this.cityId,
    required this.predictedPrice,
    required this.currency,
    required this.confidenceInterval,
    required this.latencyMs,
    required this.modelVersion,
  });

  factory PredictionResult.fromJson(Map<String, dynamic> json) =>
      PredictionResult(
        predictionId: json['prediction_id'] as String,
        cityId: json['city_id'] as String,
        predictedPrice: (json['predicted_price'] as num).toDouble(),
        currency: json['currency'] as String,
        confidenceInterval: ConfidenceInterval.fromJson(
            json['confidence_interval'] as Map<String, dynamic>),
        latencyMs: (json['latency_ms'] as num).toDouble(),
        modelVersion: json['model_version'] as String,
      );
}

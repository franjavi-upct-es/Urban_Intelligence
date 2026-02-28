// frontend/src/pages/Predict.tsx
// Urban Intelligence Framework - Price Prediction Page

import { useState } from "react";
import { TrendingUp, Info, Loader2 } from "lucide-react";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
  Button,
  Input,
  Select,
  Badge,
} from "@/components/ui";
import { usePrediction } from "@/hooks";
import { PredictionFormData, DEFAULT_PREDICTION_FORM, RoomType } from "@/types";
import { formatCurrency, cn } from "@/utils";

const ROOM_TYPES: { value: RoomType; label: string }[] = [
  { value: "Entire home/apt", label: "Entire home/apt" },
  { value: "Private room", label: "Private room" },
  { value: "Shared room", label: "Shared room" },
  { value: "Hotel room", label: "Hotel room" },
];

const PROPERTY_TYPES = [
  { value: "Apartment", label: "Apartment" },
  { value: "House", label: "House" },
  { value: "Condominium", label: "Condominium" },
  { value: "Loft", label: "Loft" },
  { value: "Villa", label: "Villa" },
  { value: "Townhouse", label: "Townhouse" },
];

export function Predict() {
  const [formData, setFormData] = useState<PredictionFormData>(
    DEFAULT_PREDICTION_FORM,
  );
  const prediction = usePrediction();

  const handleInputChange = (
    field: keyof PredictionFormData,
    value: string | number | boolean,
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    prediction.mutate(formData);
  };

  const handleReset = () => {
    setFormData(DEFAULT_PREDICTION_FORM);
    prediction.reset();
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Price Prediction
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Enter listing details to get an estimated nightly price
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Prediction Form */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-primary-600" />
                Listing Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Property Info */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Select
                    label="Room Type"
                    options={ROOM_TYPES}
                    value={formData.room_type}
                    onChange={(e) =>
                      handleInputChange("room_type", e.target.value as RoomType)
                    }
                  />
                  <Select
                    label="Property Type"
                    options={PROPERTY_TYPES}
                    value={formData.property_type}
                    onChange={(e) =>
                      handleInputChange("property_type", e.target.value)
                    }
                  />
                </div>

                {/* Capacity */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Input
                    label="Guests"
                    type="number"
                    min={1}
                    max={20}
                    value={formData.accommodates}
                    onChange={(e) =>
                      handleInputChange(
                        "accommodates",
                        parseInt(e.target.value),
                      )
                    }
                  />
                  <Input
                    label="Bedrooms"
                    type="number"
                    min={0}
                    max={20}
                    value={formData.bedrooms}
                    onChange={(e) =>
                      handleInputChange("bedrooms", parseInt(e.target.value))
                    }
                  />
                  <Input
                    label="Beds"
                    type="number"
                    min={0}
                    max={30}
                    value={formData.beds}
                    onChange={(e) =>
                      handleInputChange("beds", parseInt(e.target.value))
                    }
                  />
                  <Input
                    label="Bathrooms"
                    type="number"
                    min={0}
                    max={10}
                    step={0.5}
                    value={formData.bathrooms}
                    onChange={(e) =>
                      handleInputChange("bathrooms", parseFloat(e.target.value))
                    }
                  />
                </div>

                {/* Location */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    label="Latitude"
                    type="number"
                    step="any"
                    value={formData.latitude}
                    onChange={(e) =>
                      handleInputChange("latitude", parseFloat(e.target.value))
                    }
                  />
                  <Input
                    label="Longitude"
                    type="number"
                    step="any"
                    value={formData.longitude}
                    onChange={(e) =>
                      handleInputChange("longitude", parseFloat(e.target.value))
                    }
                  />
                </div>

                {/* Booking Details */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Input
                    label="Min Nights"
                    type="number"
                    min={1}
                    value={formData.minimum_nights}
                    onChange={(e) =>
                      handleInputChange(
                        "minimum_nights",
                        parseInt(e.target.value),
                      )
                    }
                  />
                  <Input
                    label="Availability (days)"
                    type="number"
                    min={0}
                    max={365}
                    value={formData.availability_365}
                    onChange={(e) =>
                      handleInputChange(
                        "availability_365",
                        parseInt(e.target.value),
                      )
                    }
                  />
                  <Input
                    label="Reviews"
                    type="number"
                    min={0}
                    value={formData.number_of_reviews}
                    onChange={(e) =>
                      handleInputChange(
                        "number_of_reviews",
                        parseInt(e.target.value),
                      )
                    }
                  />
                  <Input
                    label="Rating"
                    type="number"
                    min={0}
                    max={5}
                    step={0.1}
                    value={formData.review_scores_rating}
                    onChange={(e) =>
                      handleInputChange(
                        "review_scores_rating",
                        parseFloat(e.target.value),
                      )
                    }
                  />
                </div>

                {/* Toggles */}
                <div className="flex flex-wrap gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.instant_bookable}
                      onChange={(e) =>
                        handleInputChange("instant_bookable", e.target.checked)
                      }
                      className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      Instant Bookable
                    </span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.host_is_superhost}
                      onChange={(e) =>
                        handleInputChange("host_is_superhost", e.target.checked)
                      }
                      className="w-4 h-4 text-primary-600 rounded focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      Superhost
                    </span>
                  </label>
                </div>

                {/* Buttons */}
                <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                  <Button type="submit" loading={prediction.isPending}>
                    {prediction.isPending ? "Predicting..." : "Predict Price"}
                  </Button>
                  <Button type="button" variant="outline" onClick={handleReset}>
                    Reset
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Prediction Result */}
        <div className="space-y-6">
          <Card className={cn(prediction.data && "ring-2 ring-primary-500")}>
            <CardHeader>
              <CardTitle>Prediction Result</CardTitle>
            </CardHeader>
            <CardContent>
              {prediction.isPending ? (
                <div className="flex flex-col items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                  <p className="mt-2 text-sm text-gray-500">Analyzing...</p>
                </div>
              ) : prediction.data ? (
                <div className="space-y-4">
                  <div className="text-center py-4">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Predicted Price
                    </p>
                    <p className="text-4xl font-bold text-primary-600 mt-1">
                      {formatCurrency(prediction.data.predicted_price)}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      per night
                    </p>
                  </div>

                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Confidence Interval (95%)
                    </p>
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-semibold">
                        {formatCurrency(prediction.data.confidence_interval[0])}
                      </span>
                      <span className="text-gray-400">—</span>
                      <span className="text-lg font-semibold">
                        {formatCurrency(prediction.data.confidence_interval[1])}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-500">Model Version</span>
                    <Badge variant="info">
                      {prediction.data.model_version}
                    </Badge>
                  </div>
                </div>
              ) : prediction.isError ? (
                <div className="text-center py-8">
                  <p className="text-red-500">Failed to get prediction</p>
                  <p className="text-sm text-gray-500 mt-1">Please try again</p>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Info className="w-12 h-12 text-gray-300 mx-auto" />
                  <p className="text-gray-500 mt-2">
                    Fill in the form and click Predict
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tips Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Pricing Tips</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
              <div className="flex items-start gap-2">
                <span className="text-primary-500">•</span>
                <span>
                  Entire homes typically command 2-3x higher prices than private
                  rooms
                </span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-primary-500">•</span>
                <span>Superhost status can increase prices by 10-15%</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-primary-500">•</span>
                <span>
                  Central locations in popular neighborhoods get premium pricing
                </span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-primary-500">•</span>
                <span>
                  Higher review scores correlate with higher acceptable prices
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default Predict;

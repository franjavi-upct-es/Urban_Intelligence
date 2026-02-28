// frontend/src/pages/Experiments.tsx
// Urban Intelligence Framework - A/B Testing Dashboard

import { useState } from "react";
import {
  FlaskConical,
  Play,
  Pause,
  Plus,
  TrendingUp,
  Users,
  BarChart3,
} from "lucide-react";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
  Button,
  Badge,
  Input,
  Select,
  EmptyState,
  Spinner,
} from "@/components/ui";
import { useExperiments, useStartExperiment, useStopExperiment } from "@/hooks";
import { Experiment, ExperimentStatus } from "@/types";
import { formatNumber, formatPercentage, cn } from "@/utils";

export function Experiments() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const { data: experiments, isLoading } = useExperiments();
  const startExperiment = useStartExperiment();
  const stopExperiment = useStopExperiment();

  const activeExperiments =
    experiments?.filter((e) => e.status === "running") || [];
  const completedExperiments =
    experiments?.filter((e) => e.status === "completed") || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            A/B Experiments
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Compare model versions and measure performance
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          New Experiment
        </Button>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="flex items-center gap-4 py-4">
            <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-full">
              <Play className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{activeExperiments.length}</p>
              <p className="text-sm text-gray-500">Running</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 py-4">
            <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-full">
              <BarChart3 className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {completedExperiments.length}
              </p>
              <p className="text-sm text-gray-500">Completed</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-4 py-4">
            <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-full">
              <Users className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {formatNumber(
                  experiments?.reduce(
                    (sum, e) => sum + e.metrics.total_predictions,
                    0,
                  ) || 0,
                  0,
                )}
              </p>
              <p className="text-sm text-gray-500">Total Predictions</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Active Experiments */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-primary-600" />
            Active Experiments
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner className="w-8 h-8" />
            </div>
          ) : activeExperiments.length === 0 ? (
            <EmptyState
              icon={<FlaskConical className="w-8 h-8 text-gray-400" />}
              title="No active experiments"
              description="Create a new experiment to start comparing model versions"
              action={
                <Button onClick={() => setShowCreateModal(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Experiment
                </Button>
              }
            />
          ) : (
            <div className="space-y-4">
              {activeExperiments.map((experiment) => (
                <ExperimentCard
                  key={experiment.id}
                  experiment={experiment}
                  onStart={() => startExperiment.mutate(experiment.id)}
                  onStop={() => stopExperiment.mutate(experiment.id)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Completed Experiments */}
      {completedExperiments.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Completed Experiments</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {completedExperiments.map((experiment) => (
                <ExperimentCard
                  key={experiment.id}
                  experiment={experiment}
                  completed
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateExperimentModal onClose={() => setShowCreateModal(false)} />
      )}
    </div>
  );
}

function ExperimentCard({
  experiment,
  onStart,
  onStop,
  completed = false,
}: {
  experiment: Experiment;
  onStart?: () => void;
  onStop?: () => void;
  completed?: boolean;
}) {
  const statusColors: Record<ExperimentStatus, string> = {
    draft: "bg-gray-100 text-gray-800",
    running: "bg-green-100 text-green-800",
    paused: "bg-yellow-100 text-yellow-800",
    completed: "bg-blue-100 text-blue-800",
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {experiment.name}
            </h3>
            <span
              className={cn(
                "px-2 py-0.5 text-xs font-medium rounded-full",
                statusColors[experiment.status],
              )}
            >
              {experiment.status}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1">{experiment.description}</p>
        </div>
        {!completed && (
          <div className="flex gap-2">
            {experiment.status === "running" ? (
              <Button size="sm" variant="outline" onClick={onStop}>
                <Pause className="w-4 h-4 mr-1" />
                Stop
              </Button>
            ) : (
              <Button size="sm" onClick={onStart}>
                <Play className="w-4 h-4 mr-1" />
                Start
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Variants */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        {experiment.variants.map((variant) => (
          <div
            key={variant.id}
            className={cn(
              "p-4 rounded-lg border",
              experiment.metrics.winner === variant.id
                ? "border-green-500 bg-green-50 dark:bg-green-900/20"
                : "border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700/50",
            )}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium">{variant.name}</span>
              <Badge variant="default">
                {variant.traffic_percentage}% traffic
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="text-gray-500">Model</p>
                <p className="font-mono text-xs">{variant.model_version}</p>
              </div>
              <div>
                <p className="text-gray-500">Predictions</p>
                <p>{formatNumber(variant.predictions_count, 0)}</p>
              </div>
              <div>
                <p className="text-gray-500">MAE</p>
                <p>${formatNumber(variant.metrics.mae || 0, 2)}</p>
              </div>
              <div>
                <p className="text-gray-500">RMSE</p>
                <p>${formatNumber(variant.metrics.rmse || 0, 2)}</p>
              </div>
            </div>
            {experiment.metrics.winner === variant.id && (
              <div className="mt-2 flex items-center gap-1 text-green-600 text-sm">
                <TrendingUp className="w-4 h-4" />
                Winner with {formatPercentage(experiment.metrics.lift)} lift
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Results Summary */}
      {completed && experiment.metrics.winner && (
        <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <p className="text-sm text-green-800 dark:text-green-400">
            <strong>Result:</strong> Variant "{experiment.metrics.winner}" won
            with {formatPercentage(experiment.metrics.confidence)} confidence
            and {formatPercentage(experiment.metrics.lift)} improvement in MAE.
          </p>
        </div>
      )}
    </div>
  );
}

function CreateExperimentModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-lg mx-4">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold">Create New Experiment</h2>
        </div>
        <div className="p-6 space-y-4">
          <Input
            label="Experiment Name"
            placeholder="e.g., XGBoost vs LightGBM"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Input
            label="Description"
            placeholder="Brief description of the experiment"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <div className="grid grid-cols-2 gap-4">
            <Select
              label="Variant A Model"
              options={[
                { value: "v1.0.0", label: "XGBoost v1.0.0" },
                { value: "v1.1.0", label: "XGBoost v1.1.0" },
                { value: "v2.0.0", label: "LightGBM v2.0.0" },
              ]}
            />
            <Select
              label="Variant B Model"
              options={[
                { value: "v1.0.0", label: "XGBoost v1.0.0" },
                { value: "v1.1.0", label: "XGBoost v1.1.0" },
                { value: "v2.0.0", label: "LightGBM v2.0.0" },
              ]}
            />
          </div>
        </div>
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={onClose}>Create Experiment</Button>
        </div>
      </div>
    </div>
  );
}

export default Experiments;

// frontend/src/pages/ExperimentsPage.tsx
// Urban Intelligence Framework v2.0.0
// A/B testing experiments page — create, manage, and analyse experiments

import { useState } from "react";
import {
  FlaskConical,
  Play,
  CheckSquare,
  Plus,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import {
  useExperiments,
  useCreateExperiment,
  useStartExperiment,
  useCompleteExperiment,
} from "@/hooks";
import {
  SectionHeader,
  FullPageSpinner,
  ErrorBanner,
  Badge,
  EmptyState,
  Table,
} from "@/components/ui";
import type {
  Experiment,
  ExperimentStatus,
  CreateExperimentRequest,
} from "@/types";

// ── Status badge helper ───────────────────────────────────────────────────

function statusBadge(status: ExperimentStatus) {
  const map: Record<ExperimentStatus, "blue" | "green" | "yellow" | "gray"> = {
    draft: "gray",
    running: "blue",
    paused: "yellow",
    completed: "green",
  };
  return <Badge variant={map[status]}>{status}</Badge>;
}

// ── Create experiment form ────────────────────────────────────────────────

function CreateExperimentForm({ onClose }: { onClose: () => void }) {
  const createExp = useCreateExperiment();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [variants, setVariants] = useState([
    { name: "control", model_id: "xgb_v1", traffic_split: 0.5 },
    { name: "treatment", model_id: "ensemble_v2", traffic_split: 0.5 },
  ]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const req: CreateExperimentRequest = { name, description, variants };
    createExp.mutate(req, { onSuccess: onClose });
  }

  function updateVariant(idx: number, field: string, value: string | number) {
    setVariants((prev) =>
      prev.map((v, i) => (i === idx ? { ...v, [field]: value } : v)),
    );
  }

  return (
    <div className="card p-6 space-y-4 animate-slide-up">
      <h3 className="font-semibold text-slate-200">New Experiment</h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Name</label>
            <input
              className="input"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. XGBoost vs Ensemble"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">
              Description
            </label>
            <input
              className="input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional"
            />
          </div>
        </div>

        <div>
          <p className="text-xs text-slate-500 mb-2">
            Variants (splits must sum to 1.0)
          </p>
          <div className="space-y-2">
            {variants.map((v, idx) => (
              <div key={idx} className="grid grid-cols-3 gap-3">
                <input
                  className="input text-sm"
                  placeholder="Variant name"
                  value={v.name}
                  onChange={(e) => updateVariant(idx, "name", e.target.value)}
                />
                <input
                  className="input text-sm"
                  placeholder="Model ID"
                  value={v.model_id}
                  onChange={(e) =>
                    updateVariant(idx, "model_id", e.target.value)
                  }
                />
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.05}
                  className="input text-sm"
                  value={v.traffic_split}
                  onChange={(e) =>
                    updateVariant(
                      idx,
                      "traffic_split",
                      parseFloat(e.target.value),
                    )
                  }
                />
              </div>
            ))}
          </div>
        </div>

        {createExp.isError && (
          <ErrorBanner message={(createExp.error as Error).message} />
        )}

        <div className="flex gap-3 justify-end">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="btn-primary"
            disabled={createExp.isPending}
          >
            {createExp.isPending ? "Creating…" : "Create Experiment"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ── Experiment row ────────────────────────────────────────────────────────

function ExperimentRow({ exp }: { exp: Experiment }) {
  const [expanded, setExpanded] = useState(false);
  const start = useStartExperiment();
  const complete = useCompleteExperiment();

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FlaskConical size={16} className="text-brand-400" />
          <span className="font-medium text-slate-200">{exp.name}</span>
          {statusBadge(exp.status)}
        </div>
        <div className="flex items-center gap-2">
          {exp.status === "draft" && (
            <button
              onClick={() => start.mutate(exp.id)}
              className="btn-primary text-xs flex items-center gap-1.5 px-3 py-1.5"
            >
              <Play size={12} /> Start
            </button>
          )}
          {exp.status === "running" && (
            <button
              onClick={() => complete.mutate(exp.id)}
              className="btn-secondary text-xs flex items-center gap-1.5 px-3 py-1.5"
            >
              <CheckSquare size={12} /> Complete
            </button>
          )}
          <button
            className="text-slate-500 hover:text-slate-300"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="pt-2 border-t border-slate-700/50 space-y-3 animate-fade-in">
          <p className="text-xs text-slate-500">
            Created: {new Date(exp.created_at).toLocaleString()}
          </p>
          <Table
            headers={[
              "Variant",
              "Model ID",
              "Traffic Split",
              "Samples",
              "RMSE",
              "MAE",
            ]}
            rows={exp.variants.map((v) => [
              v.name,
              v.model_id,
              `${(v.traffic_split * 100).toFixed(0)}%`,
              v.n_samples,
              v.rmse != null ? v.rmse.toFixed(4) : "—",
              v.mae != null ? v.mae.toFixed(4) : "—",
            ])}
          />
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function ExperimentsPage() {
  const { data, isLoading, error } = useExperiments();
  const [showCreate, setShowCreate] = useState(false);

  const experiments = data?.experiments ?? [];

  if (isLoading) return <FullPageSpinner message="Loading experiments…" />;
  if (error) return <ErrorBanner message="Failed to load experiments." />;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Experiments"
        subtitle="A/B testing framework for model comparison"
        action={
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={16} /> New Experiment
          </button>
        }
      />

      {showCreate && (
        <CreateExperimentForm onClose={() => setShowCreate(false)} />
      )}

      {experiments.length === 0 ? (
        <EmptyState
          title="No experiments yet"
          description="Create an experiment to start comparing models"
          action={
            <button
              onClick={() => setShowCreate(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Plus size={16} /> Create First Experiment
            </button>
          }
        />
      ) : (
        <div className="space-y-3">
          {experiments.map((exp) => (
            <ExperimentRow key={exp.id} exp={exp} />
          ))}
        </div>
      )}
    </div>
  );
}

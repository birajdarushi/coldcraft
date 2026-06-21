import { useState } from "react";
import { GitBranch, BookOpen, CheckSquare, Square, Play, Sparkles, Loader2, ArrowRight } from "lucide-react";
import AppShell from "../components/AppShell.jsx";
import { Button, Panel, Field, Input, Textarea, Overline, Tag, Banner, Loading, ErrorBlock } from "../components/ui.jsx";
import { api } from "../lib/api.js";

export default function Roadmap() {
  const [title, setTitle] = useState("");
  const [syllabus, setSyllabus] = useState("");
  const [roadmap, setRoadmap] = useState(null);
  
  const [generating, setGenerating] = useState(false);
  const [updatingNode, setUpdatingNode] = useState(null);
  const [error, setError] = useState(null);

  async function handleGenerate(e) {
    e.preventDefault();
    if (!title.trim()) return;
    setGenerating(true);
    setError(null);
    setRoadmap(null);
    try {
      const res = await api.generateRoadmap({ title, syllabus });
      setRoadmap(res);
    } catch (err) {
      setError(err.detail || "Failed to generate roadmap.");
    } finally {
      setGenerating(false);
    }
  }

  async function toggleNodeStatus(nodeId, currentStatus) {
    if (!roadmap) return;
    setUpdatingNode(nodeId);
    setError(null);
    const nextCompleted = currentStatus !== "completed";
    const nextStatus = nextCompleted ? "completed" : "not_started";
    
    try {
      const updated = await api.updateRoadmapNode(roadmap.id, nodeId, {
        completed: nextCompleted,
        status: nextStatus
      });
      setRoadmap(updated);
    } catch (err) {
      setError(err.detail || "Failed to update node progress.");
    } finally {
      setUpdatingNode(null);
    }
  }

  const nodes = roadmap?.nodes?.nodes || [];
  const edges = roadmap?.nodes?.edges || [];

  return (
    <AppShell title="Skill Roadmap" subtitle="// OUTCOME MAPS · AI-GENERATED SYLLABUS & PROGRESS MATRIX">
      <div className="p-4 grid grid-cols-1 lg:grid-cols-3 gap-4 max-w-7xl">
        {/* Left Column: Input Form */}
        <div className="space-y-4 lg:col-span-1">
          <Panel title="Plan Out a Skill" code="roadmap generator">
            <form onSubmit={handleGenerate} className="space-y-4">
              <p className="font-mono text-[10px] text-muted-foreground">
                Enter any language, library, concept, or tool to generate a visual milestone graph using LLM reasoning.
              </p>
              
              <Field label="Target Skill" hint="required">
                <Input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Kubernetes, Go microservices, Rust"
                  required
                  disabled={generating}
                />
              </Field>

              <Field label="Optional Syllabus Details">
                <Textarea
                  rows={4}
                  value={syllabus}
                  onChange={(e) => setSyllabus(e.target.value)}
                  placeholder="e.g. Focus on docker deployment, CI/CD, AWS EKS. Skip basics."
                  disabled={generating}
                />
              </Field>

              {error && <Banner tone="error">{error}</Banner>}

              <Button type="submit" variant="primary" className="w-full" disabled={generating || !title.trim()}>
                {generating ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Generating Nodes...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    Generate Node Graph
                  </>
                )}
              </Button>
            </form>
          </Panel>
        </div>

        {/* Right Column: Node Graph Visualizer */}
        <div className="lg:col-span-2 space-y-4">
          <Panel
            title={roadmap ? `Roadmap: ${roadmap.title}` : "Roadmap Visualizer"}
            code={roadmap ? `id: ${roadmap.id.slice(0, 8)}` : "graph node renderer"}
          >
            {generating ? (
              <div className="py-20 flex flex-col items-center justify-center">
                <Loading label="COMPILING SYLLABUS BLOCKS VIA GEMINI..." />
                <p className="font-mono text-[10px] text-muted-foreground/70 mt-2 max-w-sm text-center">
                  This analyzes the domain structure, designs pre-requisite nodes, and fetches references.
                </p>
              </div>
            ) : !roadmap ? (
              <div className="border border-dashed border-border p-16 text-center text-muted-foreground font-mono text-[12px] rounded-sm">
                NO ACTIVE GRAPH. SUBMIT A SKILL TARGET ON THE LEFT TO RENDER NODES.
              </div>
            ) : (
              <div className="space-y-6">
                <Banner tone="info">
                  Interactive Node Graph: Click the checkbox on any milestone to mark it completed. Prerequisites are connected by visual edges.
                </Banner>
                {/* VISUAL TREE/LIST NODE SYSTEM */}
                <div className="relative border border-border bg-background p-6 rounded-sm space-y-8 overflow-hidden">
                  
                  {/* Decorative background grid lines */}
                  <div className="absolute inset-0 grid-bg opacity-10 pointer-events-none" />

                  {roadmap?.nodes?.phases && roadmap.nodes.phases.length > 0 ? (
                    <div className="space-y-10 relative z-10 w-full">
                      {roadmap.nodes.phases.map((phase) => (
                        <div key={phase.phase_number} className="border border-border/60 bg-surface/30 p-5 rounded-sm relative">
                          {/* Phase Header */}
                          <div className="mb-4 pb-3 border-b border-border/40 flex flex-wrap items-center justify-between gap-2">
                            <div>
                              <span className="font-mono text-[9px] text-emerald-400 uppercase tracking-widest block font-bold">
                                Phase {phase.phase_number}
                              </span>
                              <h3 className="font-sans font-extrabold text-[15px] text-foreground leading-normal mt-0.5">
                                {phase.title}
                              </h3>
                              {phase.description && (
                                <p className="font-mono text-[10px] text-muted-foreground mt-1">
                                  {phase.description}
                                </p>
                              )}
                            </div>
                          </div>

                          {/* Nodes in Phase */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {phase.nodes.map((node) => {
                              const isCompleted = node.status === "completed";
                              const isUpdating = updatingNode === node.id;

                              return (
                                <div
                                  key={node.id}
                                  className={`border p-3.5 bg-surface rounded-sm transition-all flex flex-col justify-between ${
                                    isCompleted 
                                      ? "border-emerald-500/40 shadow-emerald-500/5 bg-emerald-500/[0.02]" 
                                      : "border-border hover:border-foreground/35"
                                  }`}
                                >
                                  <div>
                                    <div className="flex items-start justify-between gap-2">
                                      <div className="flex items-start gap-2.5">
                                        <button
                                          onClick={() => toggleNodeStatus(node.id, node.status)}
                                          disabled={isUpdating}
                                          className={`mt-0.5 transition-colors ${
                                            isCompleted ? "text-emerald-500" : "text-muted-foreground hover:text-foreground"
                                          }`}
                                          title={isCompleted ? "Mark incomplete" : "Mark completed"}
                                        >
                                          {isUpdating ? (
                                            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                                          ) : isCompleted ? (
                                            <CheckSquare className="w-4.5 h-4.5" />
                                          ) : (
                                            <Square className="w-4.5 h-4.5" />
                                          )}
                                        </button>
                                        <div>
                                          <h4 className="font-sans font-extrabold text-[13px] text-foreground leading-normal">
                                            {node.label}
                                          </h4>
                                          {node.duration && (
                                            <span className="font-mono text-[9px] text-amber-500 uppercase tracking-wider mt-0.5 block">
                                              ⏱ {node.duration}
                                            </span>
                                          )}
                                        </div>
                                      </div>
                                      <Tag className={isCompleted ? "border-emerald-500/25 text-emerald-400" : "border-border/60"}>
                                        {node.status}
                                      </Tag>
                                    </div>

                                    {node.description && (
                                      <p className="font-sans text-[11px] text-muted-foreground mt-2 leading-relaxed">
                                        {node.description}
                                      </p>
                                    )}

                                    {/* Subtopics */}
                                    {node.subtopics && node.subtopics.length > 0 && (
                                      <div className="mt-2.5 space-y-1">
                                        <span className="font-mono text-[8px] text-muted-foreground/80 tracking-wider uppercase block">
                                          Core Concepts:
                                        </span>
                                        <div className="flex flex-wrap gap-1">
                                          {node.subtopics.map((sub, i) => (
                                            <span key={i} className="font-mono text-[9px] bg-muted/30 px-1.5 py-0.5 rounded-xs border border-border/20 text-foreground/80">
                                              {sub}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>

                                  {/* Resources */}
                                  {node.resources && node.resources.length > 0 && (
                                    <div className="mt-3 pt-2.5 border-t border-border/30 space-y-1">
                                      <span className="font-mono text-[8px] text-muted-foreground tracking-wider uppercase block">
                                        Links & Docs:
                                      </span>
                                      <div className="flex flex-col gap-1">
                                        {node.resources.map((res, i) => (
                                          <a
                                            key={i}
                                            href={res.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="inline-flex items-center gap-1 font-mono text-[9px] text-blue-400 hover:text-blue-300 hover:underline"
                                          >
                                            <BookOpen className="w-2.5 h-2.5 text-muted-foreground" />
                                            {res.title}
                                          </a>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    // Flat fallback list
                    <div className="space-y-6 w-full max-w-md mx-auto relative z-10 flex flex-col items-center">
                      {nodes.map((node, index) => {
                        const isCompleted = node.status === "completed";
                        const isUpdating = updatingNode === node.id;

                        return (
                          <div key={node.id} className="relative z-10 w-full flex flex-col">
                            {index < nodes.length - 1 && (
                              <div className="absolute left-1/2 -bottom-8 w-px h-8 border-l border-dashed border-border flex items-center justify-center pointer-events-none">
                                <div className="w-1.5 h-1.5 border-r border-b border-border rotate-45 transform translate-y-1" />
                              </div>
                            )}

                            <div
                              className={`border p-3.5 bg-surface rounded-sm transition-all ${
                                isCompleted 
                                  ? "border-emerald-500/40 shadow-emerald-500/5 bg-emerald-500/[0.02]" 
                                  : "border-border hover:border-foreground/35"
                              }`}
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div className="flex items-start gap-2.5">
                                  <button
                                    onClick={() => toggleNodeStatus(node.id, node.status)}
                                    disabled={isUpdating}
                                    className={`mt-0.5 transition-colors ${
                                      isCompleted ? "text-emerald-500" : "text-muted-foreground hover:text-foreground"
                                    }`}
                                    title={isCompleted ? "Mark incomplete" : "Mark completed"}
                                  >
                                    {isUpdating ? (
                                      <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                                    ) : isCompleted ? (
                                      <CheckSquare className="w-4.5 h-4.5" />
                                    ) : (
                                      <Square className="w-4.5 h-4.5" />
                                    )}
                                  </button>
                                  <div>
                                    <span className="font-mono text-[9px] text-muted-foreground uppercase tracking-widest block">
                                      Milestone {index + 1}
                                    </span>
                                    <h4 className="font-sans font-extrabold text-[13px] text-foreground leading-normal mt-0.5">
                                      {node.label}
                                    </h4>
                                  </div>
                                </div>
                                <Tag className={isCompleted ? "border-emerald-500/25 text-emerald-400" : "border-border/60"}>
                                  {node.status}
                                </Tag>
                              </div>

                              {node.resources && node.resources.length > 0 && (
                                <div className="mt-3 pt-2.5 border-t border-border/30 space-y-1">
                                  <span className="font-mono text-[9px] text-muted-foreground tracking-wider uppercase block">
                                    Resources & References:
                                  </span>
                                  {node.resources.map((res, i) => (
                                    <a
                                      key={i}
                                      href={res.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-1 font-mono text-[10px] text-blue-400 hover:text-blue-300 hover:underline"
                                    >
                                      <BookOpen className="w-3 h-3 text-muted-foreground" />
                                      {res.title}
                                    </a>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}
          </Panel>
        </div>
      </div>
    </AppShell>
  );
}

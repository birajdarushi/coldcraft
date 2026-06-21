import logging
import os
from fastapi import APIRouter, HTTPException
from ..schemas import RoadmapCreate, NodeStatusUpdate, RoadmapResponse
from ... import llm

logger = logging.getLogger(__name__)


def generate_stub_roadmap(title: str) -> dict:
    slug = title.lower().replace(" ", "-")
    phases = [
        {
            "phase_number": 1,
            "title": "Phase 1: Foundations",
            "description": f"Learn the absolute basics of {title}.",
            "nodes": [
                {
                    "id": "1",
                    "label": "Introduction & Syntax",
                    "description": f"Core concepts, setup, and first steps with {title}.",
                    "status": "not_started",
                    "duration": "1 week",
                    "subtopics": ["Installation", "Basic Syntax", "Data Types", "Variables"],
                    "resources": [{"title": f"Intro to {title}", "url": f"https://example.com/learn/{slug}"}]
                }
            ]
        },
        {
            "phase_number": 2,
            "title": "Phase 2: Core Concepts",
            "description": f"Deepen your understanding and build working applications.",
            "nodes": [
                {
                    "id": "2",
                    "label": "Intermediate Structure",
                    "description": "Control flow, concurrency, interfaces, and architecture.",
                    "status": "not_started",
                    "duration": "2 weeks",
                    "subtopics": ["Functions", "Control Flow", "Modules", "Error Handling"],
                    "resources": [{"title": f"Intermediate {title}", "url": f"https://example.com/learn/{slug}-intermediate"}]
                }
            ]
        },
        {
            "phase_number": 3,
            "title": "Phase 3: Advanced Topics",
            "description": "Production preparation, performance tuning, and ecosystems.",
            "nodes": [
                {
                    "id": "3",
                    "label": "Advanced & Deployment",
                    "description": "Scaling, testing, debugging, and production best practices.",
                    "status": "not_started",
                    "duration": "2 weeks",
                    "subtopics": ["Testing", "Optimization", "Deployment", "Best Practices"],
                    "resources": [{"title": f"Advanced {title}", "url": f"https://example.com/learn/{slug}-advanced"}]
                }
            ]
        }
    ]
    
    # Flat lists for backward compatibility
    flat_nodes = []
    for p in phases:
        for n in p["nodes"]:
            flat_nodes.append({
                "id": n["id"],
                "label": n["label"],
                "status": n["status"],
                "resources": n["resources"],
                "dependencies": [str(int(n["id"]) - 1)] if int(n["id"]) > 1 else []
            })
            
    edges = [
        {"source": "1", "target": "2"},
        {"source": "2", "target": "3"}
    ]
    
    return {
        "phases": phases,
        "nodes": flat_nodes,
        "edges": edges
    }


def get_roadmaps_router(campaigns_repo) -> APIRouter:
    router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])

    @router.post("", response_model=RoadmapResponse)
    def generate_roadmap(body: RoadmapCreate):
        gemini_key = campaigns_repo.get_gemini_api_key() or os.environ.get("GEMINI_API_KEY")
        nodes_graph = None

        if gemini_key:
            try:
                system = "You are a senior engineering mentor. Respond ONLY with a JSON object."
                syllabus_part = f"\nOptional Syllabus: {body.syllabus}" if body.syllabus else ""
                prompt = (
                    f"Generate a structured learning roadmap for the target skill: '{body.title}'.{syllabus_part}\n\n"
                    "Produce a JSON object with exactly one key: 'phases'. The value of 'phases' should be a list of phases representing a progression. "
                    "Each phase represents a milestone section and has:\n"
                    "   - 'phase_number': An integer (e.g. 1, 2, 3)\n"
                    "   - 'title': Short, descriptive title of the phase (e.g. 'Phase 1: Language Syntax')\n"
                    "   - 'description': 1-2 sentence description of the goal of this phase\n"
                    "   - 'nodes': A list of key topics in this phase. Each topic/node has:\n"
                    "       - 'id': A unique string ID (sequentially '1', '2', '3', etc., across all phases)\n"
                    "       - 'label': Short name of the topic\n"
                    "       - 'description': Brief explanation of what to learn/focus on in this topic\n"
                    "       - 'status': Set to 'not_started'\n"
                    "       - 'duration': Estimated completion time (e.g. '1 week')\n"
                    "       - 'subtopics': A list of 3-5 subtopics or bullet points to learn\n"
                    "       - 'resources': A list of objects with 'title' (resource name) and 'url' (real/suggested documentation/tutorial links)\n\n"
                    "Keep the roadmap concise (3 to 4 phases, and 1 to 2 topics/nodes per phase, total of 5 to 8 nodes). Use high-quality reference links. Respond with JSON only. No preamble."
                )
                res = llm.generate_json(system=system, prompt=prompt)
                if isinstance(res, dict) and "phases" in res:
                    phases = res["phases"]
                    flat_nodes = []
                    edges = []
                    node_ids = []
                    for p in phases:
                        for n in p.get("nodes", []):
                            nid = str(n.get("id"))
                            node_ids.append(nid)
                            flat_nodes.append({
                                "id": nid,
                                "label": n.get("label", ""),
                                "status": n.get("status", "not_started"),
                                "resources": n.get("resources", []),
                                "dependencies": [node_ids[-2]] if len(node_ids) > 1 else []
                            })
                    # sequential edges
                    for i in range(len(node_ids) - 1):
                        edges.append({"source": node_ids[i], "target": node_ids[i+1]})
                        
                    nodes_graph = {
                        "phases": phases,
                        "nodes": flat_nodes,
                        "edges": edges
                    }
            except Exception as exc:
                logger.warning("Gemini roadmap generation failed: %s", exc)

        if not nodes_graph:
            nodes_graph = generate_stub_roadmap(body.title)

        roadmap = campaigns_repo.create_roadmap(title=body.title, nodes=nodes_graph)
        return roadmap

    @router.get("/{roadmap_id}", response_model=RoadmapResponse)
    def get_roadmap(roadmap_id: str):
        roadmap = campaigns_repo.get_roadmap(roadmap_id)
        if not roadmap:
            raise HTTPException(status_code=404, detail="Roadmap not found")
        return roadmap

    @router.put("/{roadmap_id}/nodes/{node_id}", response_model=RoadmapResponse)
    def update_node_status(roadmap_id: str, node_id: str, body: NodeStatusUpdate = None):
        # We can accept an optional request body. If body is None or fields are None, it will toggle the status.
        completed = body.completed if body else None
        status = body.status if body else None

        updated_roadmap = campaigns_repo.update_roadmap_node_status(
            roadmap_id=roadmap_id,
            node_id=node_id,
            completed=completed,
            status=status,
        )
        if not updated_roadmap:
            raise HTTPException(status_code=404, detail="Roadmap or Node not found")
        return updated_roadmap

    return router

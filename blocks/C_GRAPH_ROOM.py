

# =====================================================
# 🏭 GRAPH ROOM IDENTITY
# =====================================================

class GraphRoomIdentity:

    VERSION = "1.0"
    ROOM = "graph_room"
    CONTRACT = "graph_room_canonical"

    @classmethod
    def export(cls):
        return {
            "room": cls.ROOM,
            "version": cls.VERSION,
            "contract": cls.CONTRACT,
            "status": "stable"
        }

# =====================================================
# 🏭 GRAPH CONTRACT FACADE
# =====================================================

class GraphContractFacade:

    def build(self, transport_contract):
        return {
            "transport": transport_contract,
            "schema": "graph_room_canonical",
            "ready": True,
        }

# =====================================================
# 🏭 GRAPH TRANSPORT CONTRACT BUILDER
# =====================================================

class GraphTransportContractBuilder:

    def build(self, render_contract, diagnostics, capabilities, trace, context):

        return {
            "version":"2.1",
            "canonical": True,
            "render_contract": render_contract,
            "diagnostics": diagnostics,
            "capabilities": capabilities,
            "trace": trace,
            "context": context,
        }

# =====================================================
# 🏭 GRAPH CONTEXT BUILDER
# =====================================================

class GraphContextBuilder:

    def build(self, semantic, mode):
        return {
            "room":"graph_room",
            "mode":mode,
            "semantic_title":getattr(semantic,"title",""),
            "transport":"canonical"
        }

# =====================================================
# 🏭 GRAPH TRACE BUILDER
# =====================================================

class GraphTraceBuilder:

    def build(self):

        return {
            "route":[
                "GraphRoom",
                "create_artifact",
                "SceneContract",
                "RenderMessage",
                "GraphBlock"
            ],
            "route_version":"1.0"
        }

# =====================================================
# 🏭 GRAPH CAPABILITY BUILDER
# =====================================================

class GraphCapabilityBuilder:

    def build(self):

        return {
            "supports": [
                "line",
                "bar",
                "scatter",
                "function",
                "knowledge"
            ],
            "renderer": "GraphBlock",
            "contract": "graph_render_contract_v1"
        }

# =====================================================
# 🏭 GRAPH DIAGNOSTIC BUILDER
# =====================================================

class GraphDiagnosticBuilder:

    def build(self, semantic, mode):

        return {
            "room":"graph_room",
            "mode":mode,
            "title":getattr(semantic,"title",""),
            "status":"ready"
        }

# =====================================================
# 🏭 GRAPH RENDER CONTRACT BUILDER
# =====================================================

class GraphRenderContractBuilder:

    def build(self, visual_payload):

        return {
            "renderer": "GraphBlock",
            "artifact_type": "graph",
            "visual_payload": visual_payload,
            "contract_version": "1.0"
        }

# =====================================================
# 🏭 GRAPH PAYLOAD BUILDER
# =====================================================

class GraphPayloadBuilder:

    def build(self, semantic, axis, series, legend, annotations, mode):

        return {
            "scene_type": "graph",
            "mode": mode,
            "title": getattr(semantic, "title", ""),
            "x_axis": getattr(axis, "x_title", ""),
            "y_axis": getattr(axis, "y_title", ""),
            "labels": getattr(series, "labels", []),
            "values": getattr(series, "values", []),
            "series": getattr(series, "series", []),
            "legend": getattr(legend, "items", []),
            "annotations": getattr(annotations, "items", []),
        }

# =====================================================
# 🏭 GRAPH MODE RESOLVER
# =====================================================

class GraphModeResolver:

    def resolve(self, semantic):

        if getattr(semantic, "knowledge_graph", None):
            return "knowledge"

        if getattr(semantic, "series", None):
            return "series"

        if getattr(semantic, "function", None):
            return "function"

        if getattr(semantic, "scatter", None):
            return "scatter"

        if getattr(semantic, "bar", None):
            return "bar"

        if getattr(semantic, "line", None):
            return "line"

        return "unknown"

# =====================================================
# 🏭 PROFESSIONAL GRAPH ROOM CORE
# =====================================================

class GraphRoom:

    ROOM_NAME = "graph_room"

    def __init__(self):

        self.intent_analyzer = GraphIntentAnalyzer()

        self.semantic_parser = GraphSemanticParser()

        self.axis_builder = GraphAxisBuilder()

        self.series_builder = GraphSeriesBuilder()

        self.legend_builder = GraphLegendBuilder()

        self.annotation_builder = GraphAnnotationBuilder()

        self.validator = GraphValidator()

        self.optimizer = GraphOptimizer()

        self.artifact_builder = GraphArtifactBuilder()

        self.mode_resolver = GraphModeResolver()

        self.payload_builder = GraphPayloadBuilder()

        self.render_contract_builder = GraphRenderContractBuilder()

        self.diagnostic_builder = GraphDiagnosticBuilder()

        self.capability_builder = GraphCapabilityBuilder()

        self.trace_builder = GraphTraceBuilder()

        self.context_builder = GraphContextBuilder()

        self.transport_contract_builder = GraphTransportContractBuilder()

        self.contract_facade = GraphContractFacade()

        self.identity = GraphRoomIdentity.export()

    def execute(self, request: str):

        intent = self.intent_analyzer.detect(request)

        semantic = self.semantic_parser.parse(
            request,
            intent
        )

        axis = self.axis_builder.build(semantic)

        series = self.series_builder.build(semantic)

        legend = self.legend_builder.build(semantic)

        annotations = self.annotation_builder.build(
            semantic
        )

        mode = self.mode_resolver.resolve(semantic)

        visual_payload = self.payload_builder.build(semantic, axis, series, legend, annotations, mode)

        render_contract = self.render_contract_builder.build(visual_payload)

        diagnostics = self.diagnostic_builder.build(semantic, mode)

        capabilities = self.capability_builder.build()

        trace = self.trace_builder.build()

        context = self.context_builder.build(semantic, mode)

        transport_contract = self.transport_contract_builder.build(
            render_contract,
            diagnostics,
            capabilities,
            trace,
            context
        )

        contract = self.contract_facade.build(
            transport_contract
        )

        graph = self.artifact_builder.build(

            transport=transport_contract,

            semantic=semantic,

            axis=axis,

            series=series,

            legend=legend,

            annotations=annotations,

            mode=mode,

            visual_payload=visual_payload,

            render_contract=render_contract,

            diagnostics=diagnostics,

            capabilities=capabilities,

            trace=trace,

            context=context,

            contract=contract,

            identity=self.identity
        )

        graph = self.validator.validate(graph)

        graph = self.optimizer.optimize(graph)

        return create_artifact(

            artifact_type="graph",

            room_source=self.ROOM_NAME,

            data=graph
        )

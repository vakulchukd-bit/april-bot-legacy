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

        graph = self.artifact_builder.build(

            semantic=semantic,

            axis=axis,

            series=series,

            legend=legend,

            annotations=annotations
        )

        graph = self.validator.validate(graph)

        graph = self.optimizer.optimize(graph)

        return create_artifact(

            artifact_type="graph",

            room_source=self.ROOM_NAME,

            data=graph
        )

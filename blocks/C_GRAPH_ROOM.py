# =====================================================
# 🏭 GRAPH PAYLOAD BUILDER
# =====================================================

class GraphPayloadBuilder:

    def build(
        self,
        semantic,
        axis,
        series,
        legend,
        annotations,
        geometry,
    ):

        return {

            "scene_type": "graph",

            "title": semantic.title,

            "graph_title": semantic.title,

            "x_axis": axis.x_title,

            "y_axis": axis.y_title,

            "labels": series.labels,

            "values": series.values,

            "series": series.series,

            "legend": legend.items,

            "annotations": annotations.items,

            "geometry": geometry,

            "metadata": {

                "room": "graph_room",

                "renderer": "GraphBlock",

                "transport": "UnifiedVisualPayload",

                "version": "2.0"
            }
        }


# =====================================================
# 🏭 GRAPH ROOM
# =====================================================

class GraphRoom:

    ...

    def __init__(self):

        ...

        self.payload_builder = GraphPayloadBuilder()

    def execute(self, request: str):

        ...

        visual_payload = self.payload_builder.build(

            semantic,

            axis,

            series,

            legend,

            annotations,

            geometry
        )

        graph = self.artifact_builder.build(

            semantic=semantic,

            axis=axis,

            series=series,

            legend=legend,

            annotations=annotations,

            visual_payload=visual_payload
        )

        graph = self.validator.validate(graph)

        graph = self.optimizer.optimize(graph)

        return create_artifact(

            artifact_type="graph",

            room_source=self.ROOM_NAME,

            data=graph
        )

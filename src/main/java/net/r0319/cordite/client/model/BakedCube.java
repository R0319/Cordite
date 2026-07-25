package net.r0319.cordite.client.model;

import org.joml.Vector3f;

import java.util.List;

/**
 * ロード時にベイク済みの1キューブ分の面データ。頂点座標はボーンpivot相対・Java座標系
 * （X符号反転＋1/16スケール適用済み、docs/design/animation-system.md 参照）で保持し、
 * 毎フレームは {@link com.mojang.blaze3d.vertex.PoseStack} の変換をかけるだけで済むようにする。
 */
public record BakedCube(List<Quad> quads) {

    public record Quad(Vector3f normal, Vertex v0, Vertex v1, Vertex v2, Vertex v3) {
        public List<Vertex> vertices() {
            return List.of(v0, v1, v2, v3);
        }
    }

    public record Vertex(float x, float y, float z, float u, float v) {}
}

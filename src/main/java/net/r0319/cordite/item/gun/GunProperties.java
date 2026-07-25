package net.r0319.cordite.item.gun;

import java.util.List;

/**
 * 銃の不変ステータス。本来は gunpack の JSON から読む想定（docs/specs/01-gunpack.md）。
 * MVP では静的プリセットで登録し、後で JSON ローダに差し替える。
 *
 * <p>発射レートは<b>実銃準拠</b>: {@code rpm} はフルオート機のサイクリックレート（毎分発射数）を表す。
 * 単発（セミオート）機ではトリガーを引ける現実的な連射上限（速射キャップ）として扱う。</p>
 *
 * @param baseDamage    基礎ダメージ
 * @param muzzleVelocity 弾速 blocks/秒（{@code ProjectileManager} の軽量弾丸トラッカーで使用）
 * @param effectiveRange 有効射程 blocks
 * @param falloffStart   減衰開始距離 blocks
 * @param rpm            発射レート（実銃のサイクリックレート/速射上限、rounds/分）
 * @param reloadSeconds  リロード秒
 * @param magSize        マガジン容量
 * @param pelletCount    1発あたりのペレット数（ショットガン以外は 1）
 * @param fireModes      対応する発射モード（実銃準拠）。先頭が既定モード。
 * @param boltType       ボルト方式（クローズド=薬室+1、オープン=薬室なし）
 */
public record GunProperties(
        float baseDamage,
        double muzzleVelocity,
        double effectiveRange,
        double falloffStart,
        int rpm,
        float reloadSeconds,
        int magSize,
        int pelletCount,
        List<FireMode> fireModes,
        BoltType boltType
) {
    /** 発射間隔（tick）。20tick/秒 なので 1200 / rpm。 */
    public int fireIntervalTicks() {
        return Math.max(1, Math.round(1200f / rpm));
    }

    /** リロード時間（tick）。 */
    public int reloadTicks() {
        return Math.max(1, Math.round(reloadSeconds * 20f));
    }

    /** 既定の発射モード。 */
    public FireMode defaultMode() {
        return fireModes.get(0);
    }

    /** {@code current} の次のモード（対応モード内で循環）。未対応値は既定へ丸める。 */
    public FireMode nextMode(FireMode current) {
        int idx = fireModes.indexOf(current);
        if (idx < 0) {
            return defaultMode();
        }
        return fireModes.get((idx + 1) % fireModes.size());
    }

    // --- 初期実装プリセット（docs/specs/02-guns.md ＋ 実銃準拠の発射モード） ---

    /** Glock: セミオートのみ、クローズドボルト。 */
    public static final GunProperties GLOCK =
            new GunProperties(5f, 120, 30, 20, 400, 1.8f, 17, 1,
                    List.of(FireMode.SINGLE), BoltType.CLOSED);

    /** AK-47: 単発／フルオート（サイクリックレート約600）、クローズドボルト。 */
    public static final GunProperties AK47 =
            new GunProperties(7f, 160, 60, 40, 600, 2.5f, 30, 1,
                    List.of(FireMode.SINGLE, FireMode.FULL_AUTO), BoltType.CLOSED);

    /** M4A1: 単発／フルオート／バースト（サイクリックレート約800）、クローズドボルト。 */
    public static final GunProperties M4A1 =
            new GunProperties(6f, 170, 60, 40, 800, 2.3f, 30, 1,
                    List.of(FireMode.SINGLE, FireMode.FULL_AUTO, FireMode.BURST), BoltType.CLOSED);
}

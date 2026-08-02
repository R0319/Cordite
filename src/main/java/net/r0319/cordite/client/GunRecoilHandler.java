package net.r0319.cordite.client;

import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.util.Mth;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.client.anim.GunRecoilState;

/**
 * {@link GunRecoilState} が計算した視点キックを、実際のプレイヤーの向きへ反映する。
 *
 * <p><b>{@code xRotO}/{@code yRotO}（前tickの向き）は触らない。</b> レンダリングは
 * {@code getViewXRot(partialTick)}＝前tick値と現在値の補間を使うため、現在値だけを動かせば
 * 次の1tickかけて滑らかに繋がる（バニラのマウス入力{@code Entity#turn}と同じ扱い）。
 * ここで{@code xRotO}も一緒に動かすと補間が効かず、カメラがtick単位でカクつく。</p>
 *
 * <p>銃を持っているかは見ない。撃った直後に持ち替えても回復（跳ね上がったぶんが戻る動き）は
 * 最後まで走り切るべきなので、条件を付けると視点がズレたまま固定されてしまう。</p>
 */
@EventBusSubscriber(modid = Cordite.MODID, value = Dist.CLIENT)
public final class GunRecoilHandler {
    private GunRecoilHandler() {}

    @SubscribeEvent
    public static void onClientTick(ClientTickEvent.Post event) {
        LocalPlayer player = Minecraft.getInstance().player;
        if (player == null) {
            GunRecoilState.reset();
            return;
        }

        GunRecoilState.ViewDelta delta = GunRecoilState.advance();
        if (delta.isZero()) {
            return;
        }
        player.setXRot(Mth.clamp(player.getXRot() + delta.pitch(), -90f, 90f));
        player.setYRot(player.getYRot() + delta.yaw());
    }
}

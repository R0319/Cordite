package net.r0319.cordite.command;

import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.suggestion.SuggestionProvider;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.ItemStack;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.r0319.cordite.Cordite;
import net.r0319.cordite.gunpack.GunDefinitions;
import net.r0319.cordite.item.gun.GunItem;

import java.util.Collection;
import java.util.List;

/**
 * Cordite固有の管理コマンド。単一アイテム化後も銃IDを短く指定できるよう、
 * gunpack定義から銃スタックを生成する。
 */
@EventBusSubscriber(modid = Cordite.MODID)
public final class CorditeCommands {
    private static final SuggestionProvider<CommandSourceStack> GUN_ID_SUGGESTIONS = (context, builder) -> {
        GunDefinitions.server().keySet().stream()
                .map(ResourceLocation::toString)
                .sorted()
                .forEach(builder::suggest);
        return builder.buildFuture();
    };

    private CorditeCommands() {}

    @SubscribeEvent
    public static void onRegisterCommands(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("cordite")
                .requires(source -> source.hasPermission(2))
                .then(Commands.literal("give")
                        .then(Commands.argument("gunId", StringArgumentType.word())
                                .suggests(GUN_ID_SUGGESTIONS)
                                .executes(context -> give(context, List.of(context.getSource().getPlayerOrException()), 1))
                                .then(Commands.argument("targets", EntityArgument.players())
                                        .executes(context -> give(context, EntityArgument.getPlayers(context, "targets"), 1))
                                        .then(Commands.argument("count", IntegerArgumentType.integer(1))
                                                .executes(context -> give(context, EntityArgument.getPlayers(context, "targets"),
                                                        IntegerArgumentType.getInteger(context, "count"))))))));
    }

    /** 定義を確認してから各対象へ渡す。未知IDは例外にせず、入力ミスをその場で知らせる。 */
    private static int give(CommandContext<CommandSourceStack> context, Collection<ServerPlayer> targets, int count) {
        String rawId = StringArgumentType.getString(context, "gunId");
        ResourceLocation gunId = ResourceLocation.tryParse(rawId);
        if (gunId == null || GunDefinitions.server(gunId) == null) {
            context.getSource().sendFailure(Component.translatable("commands.cordite.give.unknown_gun", rawId));
            return 0;
        }

        for (ServerPlayer target : targets) {
            for (int index = 0; index < count; index++) {
                ItemStack stack = GunItem.createStack(gunId);
                if (!target.getInventory().add(stack)) {
                    target.drop(stack, false);
                }
            }
        }
        if (targets.size() == 1) {
            ServerPlayer target = targets.iterator().next();
            context.getSource().sendSuccess(() -> Component.translatable("commands.cordite.give.success.single",
                    count, GunItem.createStack(gunId).getDisplayName(), target.getDisplayName()), true);
        } else {
            context.getSource().sendSuccess(() -> Component.translatable("commands.cordite.give.success.multiple",
                    count, GunItem.createStack(gunId).getDisplayName(), targets.size()), true);
        }
        return targets.size() * count;
    }
}

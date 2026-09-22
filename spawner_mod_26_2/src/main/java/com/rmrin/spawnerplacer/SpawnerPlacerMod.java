package com.rmrin.spawnerplacer;

import java.util.function.Consumer;
import net.minecraft.ChatFormatting;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.component.TooltipDisplay;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.SpawnerBlockEntity;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

@Mod(SpawnerPlacerMod.MOD_ID)
public final class SpawnerPlacerMod {
    public static final String MOD_ID = "spawnerplacer";
    private static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, MOD_ID);
    private static final DeferredRegister<CreativeModeTab> TABS = DeferredRegister.create(Registries.CREATIVE_MODE_TAB, MOD_ID);

    public static final RegistryObject<Item> ZOMBIE_SPAWNER = register("zombie_spawner", EntityTypes.ZOMBIE);
    public static final RegistryObject<Item> SKELETON_SPAWNER = register("skeleton_spawner", EntityTypes.SKELETON);
    public static final RegistryObject<Item> SPIDER_SPAWNER = register("spider_spawner", EntityTypes.SPIDER);
    public static final RegistryObject<Item> CREEPER_SPAWNER = register("creeper_spawner", EntityTypes.CREEPER);
    public static final RegistryObject<Item> ENDERMAN_SPAWNER = register("enderman_spawner", EntityTypes.ENDERMAN);
    public static final RegistryObject<Item> BLAZE_SPAWNER = register("blaze_spawner", EntityTypes.BLAZE);
    public static final RegistryObject<Item> WITCH_SPAWNER = register("witch_spawner", EntityTypes.WITCH);
    public static final RegistryObject<Item> SLIME_SPAWNER = register("slime_spawner", EntityTypes.SLIME);

    public static final RegistryObject<CreativeModeTab> SPAWNER_TAB = TABS.register("spawner_placer", () ->
            CreativeModeTab.builder().title(Component.translatable("itemGroup.spawnerplacer.spawner_placer"))
                    .icon(() -> ZOMBIE_SPAWNER.get().getDefaultInstance()).displayItems((parameters, output) -> {
                        output.accept(ZOMBIE_SPAWNER.get()); output.accept(SKELETON_SPAWNER.get());
                        output.accept(SPIDER_SPAWNER.get()); output.accept(CREEPER_SPAWNER.get());
                        output.accept(ENDERMAN_SPAWNER.get()); output.accept(BLAZE_SPAWNER.get());
                        output.accept(WITCH_SPAWNER.get()); output.accept(SLIME_SPAWNER.get());
                    }).build());

    public SpawnerPlacerMod(FMLJavaModLoadingContext context) {
        var modBusGroup = context.getModBusGroup();
        ITEMS.register(modBusGroup);
        TABS.register(modBusGroup);
    }

    private static RegistryObject<Item> register(String id, EntityType<?> type) {
        return ITEMS.register(id, () -> new ConfiguredSpawnerItem(type, new Item.Properties().setId(ITEMS.key(id))));
    }

    private static final class ConfiguredSpawnerItem extends BlockItem {
        private final EntityType<?> type;
        private ConfiguredSpawnerItem(EntityType<?> type, Properties properties) { super(Blocks.SPAWNER, properties); this.type = type; }
        @Override public InteractionResult place(BlockPlaceContext context) {
            InteractionResult result = super.place(context);
            if (result.consumesAction() && !context.getLevel().isClientSide()) {
                var level = context.getLevel(); var position = context.getClickedPos();
                if (level.getBlockEntity(position) instanceof SpawnerBlockEntity spawner) {
                    spawner.setEntityId(this.type, level.getRandom());
                    var state = level.getBlockState(position);
                    level.sendBlockUpdated(position, state, state, 3);
                }
            }
            return result;
        }
        @Override public void appendHoverText(ItemStack stack, Item.TooltipContext context, TooltipDisplay display, Consumer<Component> tooltip, TooltipFlag flag) {
            tooltip.accept(Component.translatable("tooltip.spawnerplacer.places", this.type.getDescription()).withStyle(ChatFormatting.GRAY));
        }
    }
}

package dev.mcbookshelf.ward.mixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import dev.mcbookshelf.ward.report.ReportEntry;
import dev.mcbookshelf.ward.report.ReportManager;
import net.minecraft.server.ServerAdvancementManager;
import net.minecraft.util.ProblemReporter;
import org.slf4j.Logger;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

@Mixin(ServerAdvancementManager.class)
public class ServerAdvancementManagerMixin {

    @WrapOperation(method = "validate", at = @At(value = "INVOKE", target = "Lorg/slf4j/Logger;warn(Ljava/lang/String;Ljava/lang/Object;Ljava/lang/Object;)V"))
    private void catchAdvancementValidationError(Logger logger, String message, Object id, Object report, Operation<Void> original) {
        original.call(logger, message, id, report);
        String error = ((ProblemReporter.Collector) report).getReport();
        ReportManager.report(ReportEntry.warn("minecraft:advancement", id.toString(), error));
    }
}

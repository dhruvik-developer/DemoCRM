// Line items editor with live auto-sum. Flags any mismatch against the
// expected total before submit (backend QuotationVersion.clean rejects it).

import { useFieldArray, useFormContext } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { toMoney } from "@/utils/formatters";

export default function LineItemsEditor({ disabled = false }) {
  const { control, register, watch, formState } = useFormContext();
  const { fields, append, remove } = useFieldArray({ control, name: "line_items" });

  const items = watch("line_items") ?? [];
  const computedTotal = items.reduce(
    (sum, item) => sum + Number(item?.quantity ?? 0) * Number(item?.unit_price ?? 0),
    0,
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2">
        {fields.map((field, index) => {
          const item = items[index] ?? {};
          const amount =
            Number(item.quantity ?? 0) * Number(item.unit_price ?? 0);
          return (
            <div key={field.id} className="grid grid-cols-[1fr_5rem_7rem_6rem_2rem] items-start gap-2">
              <div className="flex flex-col gap-1">
                <Input
                  placeholder="Description"
                  disabled={disabled}
                  {...register(`line_items.${index}.description`)}
                />
                {formState.errors.line_items?.[index]?.description ? (
                  <p className="text-xs text-destructive">
                    {formState.errors.line_items[index].description.message}
                  </p>
                ) : null}
              </div>
              <div className="flex flex-col gap-1">
                <Input
                  type="number"
                  min={1}
                  step={1}
                  placeholder="Qty"
                  disabled={disabled}
                  {...register(`line_items.${index}.quantity`)}
                />
                {formState.errors.line_items?.[index]?.quantity ? (
                  <p className="text-xs text-destructive">
                    {formState.errors.line_items[index].quantity.message}
                  </p>
                ) : null}
              </div>
              <div className="flex flex-col gap-1">
                <Input
                  type="number"
                  min={0.01}
                  step={0.01}
                  placeholder="Unit price"
                  disabled={disabled}
                  {...register(`line_items.${index}.unit_price`)}
                />
                {formState.errors.line_items?.[index]?.unit_price ? (
                  <p className="text-xs text-destructive">
                    {formState.errors.line_items[index].unit_price.message}
                  </p>
                ) : null}
              </div>
              <span className="pt-2 text-right text-sm tabular-nums">
                {toMoney(amount)}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="text-destructive"
                disabled={disabled || fields.length === 1}
                onClick={() => remove(index)}
              >
                ✕
              </Button>
            </div>
          );
        })}
      </div>

      <Separator />

      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">Computed total</span>
        <span className="tabular-nums">{toMoney(computedTotal)}</span>
      </div>

      {!disabled ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="w-fit"
          onClick={() => append({ description: "", quantity: 1, unit_price: "" })}
        >
          Add line item
        </Button>
      ) : null}
    </div>
  );
}

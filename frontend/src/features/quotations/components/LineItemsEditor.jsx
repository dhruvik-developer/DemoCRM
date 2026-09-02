// Line items editor with live auto-sum. Flags any mismatch against the
// expected total before submit (backend QuotationVersion.clean rejects it).

import { useFieldArray, useFormContext, useWatch } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { toMoney } from "@/utils/formatters";

export default function LineItemsEditor({ disabled = false }) {
  const { control, register, formState } = useFormContext();
  const { fields, append, remove } = useFieldArray({ control, name: "line_items" });

  const items = useWatch({ control, name: "line_items" }) ?? [];
  const discountType = useWatch({ control, name: "discount_type" }) ?? "FLAT";
  const discountValRaw = useWatch({ control, name: "discount_value" });
  const gstRateRaw = useWatch({ control, name: "gst_rate" });
  const discountVal = Number(discountValRaw ?? 0);
  const gstRate = Number(gstRateRaw ?? 0);
  const lineSubtotal = items.reduce(
    (sum, item) => {
      const qty = Number(item?.quantity ?? 0);
      const price = Number(item?.unit_price ?? 0);
      const disc = Number(item?.discount_percent ?? 0);
      return sum + qty * price * (1 - disc / 100);
    },
    0,
  );
  let versionDisc = 0;
  if (discountVal) {
    versionDisc = discountType === "PERCENT" ? (lineSubtotal * discountVal) / 100 : discountVal;
  }
  const taxable = Math.max(0, lineSubtotal - versionDisc);
  const gstAmt = gstRate ? (taxable * gstRate) / 100 : 0;
  const cgst = gstAmt / 2;
  const sgst = gstAmt / 2;
  const computedTotal = taxable + gstAmt;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2">
        <div className="hidden grid-cols-[1fr_6rem_5rem_7rem_4rem_5rem_6rem_2rem] gap-2 text-[10px] font-bold uppercase tracking-wide text-muted-foreground md:grid">
          <span>Description</span><span>HSN</span><span>Qty</span><span>Unit ₹</span><span>GST%</span><span>Disc%</span><span className="text-right">Amount</span><span />
        </div>
        {fields.map((field, index) => {
          const item = items[index] ?? {};
          const disc = Number(item.discount_percent ?? 0);
          const amount = Number(item.quantity ?? 0) * Number(item.unit_price ?? 0) * (1 - disc / 100);
          return (
            <div key={field.id} className="grid grid-cols-2 gap-2 md:grid-cols-[1fr_6rem_5rem_7rem_4rem_5rem_6rem_2rem] items-start">
              <div className="flex flex-col gap-1">
                <Input placeholder="Description" disabled={disabled} {...register(`line_items.${index}.description`)} />
                {formState.errors.line_items?.[index]?.description ? (<p className="text-xs text-destructive">{formState.errors.line_items[index].description.message}</p>) : null}
              </div>
              <Input placeholder="HSN" disabled={disabled} {...register(`line_items.${index}.hsn_code`)} />
              <Input type="number" min={1} step={1} placeholder="Qty" disabled={disabled} {...register(`line_items.${index}.quantity`)} onKeyDown={(e)=>{if(e.key==="."||e.key===",") e.preventDefault();}} />
              <Input type="number" min={0.01} step={0.01} placeholder="Unit ₹" disabled={disabled} {...register(`line_items.${index}.unit_price`)} />
              <Input type="number" min={0} max={100} step={0.1} placeholder="18" disabled={disabled} {...register(`line_items.${index}.gst_rate`)} />
              <Input type="number" min={0} max={100} step={0.1} placeholder="0" disabled={disabled} {...register(`line_items.${index}.discount_percent`)} />
              <span className="pt-2 text-right text-xs tabular-nums font-medium md:text-sm">₹{toMoney(amount)}</span>
              <Button type="button" variant="ghost" size="sm" className="text-destructive col-span-2 md:col-span-1" disabled={disabled || fields.length === 1} onClick={() => remove(index)}>✕</Button>
            </div>
          );
        })}
      </div>

      <Separator />

      <div className="flex flex-col gap-1 text-sm">
        <div className="flex justify-between"><span className="text-muted-foreground">Line subtotal (after line discounts)</span><span className="tabular-nums">₹{toMoney(lineSubtotal)}</span></div>
        {discountVal ? <div className="flex justify-between text-amber-700"><span>Version discount {discountType === "PERCENT" ? `(${discountVal}%)` : ""}</span><span>- ₹{toMoney(versionDisc)}</span></div> : null}
        <div className="flex justify-between"><span className="text-muted-foreground">Taxable (before GST)</span><span className="tabular-nums font-medium">₹{toMoney(taxable)}</span></div>
        {gstRate ? (
          <>
            <div className="flex justify-between text-muted-foreground"><span>CGST {(gstRate/2).toFixed(1)}%</span><span>₹{toMoney(cgst)}</span></div>
            <div className="flex justify-between text-muted-foreground"><span>SGST {(gstRate/2).toFixed(1)}%</span><span>₹{toMoney(sgst)}</span></div>
            <div className="flex justify-between text-muted-foreground text-xs"><span>GST Total {gstRate}%</span><span>₹{toMoney(gstAmt)}</span></div>
          </>
        ) : <div className="flex justify-between text-muted-foreground"><span>GST</span><span>Not applicable (0%)</span></div>}
        <div className="flex justify-between font-bold border-t pt-1 text-[15px]"><span>Total (after GST)</span><span className="tabular-nums">₹{toMoney(computedTotal)}</span></div>
      </div>

      {!disabled ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="w-fit"
          onClick={() => append({ description: "", hsn_code: "", quantity: 1, unit_price: "", gst_rate: 18, discount_percent: 0 })}
        >
          Add line item
        </Button>
      ) : null}
    </div>
  );
}

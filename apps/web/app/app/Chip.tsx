import { LABEL } from "@/lib/console";

const TONE: Record<string, string> = {
  approved: "good", pass: "good", declined: "bad", fail: "bad", error: "bad",
  review_required: "warn", action_required: "warn", inconclusive: "warn", not_run: "",
};

export default function Chip({ value }: { value: string }) {
  return <span className="chip" data-tone={TONE[value] ?? ""}>{LABEL[value] ?? value.replace(/_/g, " ")}</span>;
}

import Journey from "@/components/Journey";

export default async function Handoff({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <Journey mode="handoff" token={token} />;
}

import Journey from "@/components/Journey";

export default async function Start({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <Journey mode="hosted" token={token} />;
}

import { ResearchEntity } from "../../../../components/research-entity";

export default async function ResearchEntityPage({ params }: { params: Promise<{ entityId: string }> }) {
  const { entityId } = await params;
  return <ResearchEntity entityId={entityId} />;
}

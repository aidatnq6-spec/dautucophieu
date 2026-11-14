import { ThesisOnePager } from "../../../../components/thesis-one-pager";

export default async function ThesisPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = await params;
  return <ThesisOnePager symbol={symbol.toUpperCase()} />;
}

import { useParams, useSearchParams } from "react-router-dom";
import FollowUpDetail from "../components/FollowUpDetail";

export default function FollowUpDetailPage() {
  const { followUpId } = useParams();
  const [searchParams] = useSearchParams();
  const returnLeadId = searchParams.get("return_lead") ?? undefined;
  return <FollowUpDetail followUp={{ followup_id: Number(followUpId) }} variant="page" returnLeadId={returnLeadId} />;
}

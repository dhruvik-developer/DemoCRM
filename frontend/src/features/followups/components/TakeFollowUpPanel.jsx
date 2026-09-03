import FollowUpDetail from "./FollowUpDetail";

export default function TakeFollowUpPanel({ followUp, onClose }) {
  return <FollowUpDetail followUp={followUp} onClose={onClose} variant="modal" />;
}

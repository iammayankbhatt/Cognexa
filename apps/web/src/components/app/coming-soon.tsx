import { Hourglass } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";

/**
 * Honest placeholder for a feature built in a later phase. The page, route and navigation exist
 * now so the shell is complete; the phase number says when the real screen replaces this.
 */
export function ComingSoon({
  title,
  description,
  phase,
}: {
  title: string;
  description: string;
  phase: number;
}) {
  return (
    <div className="space-y-6">
      <PageHeader title={title} description={description} />
      <EmptyState
        icon={<Hourglass />}
        title="Not available yet"
        description={`This screen is built in Phase ${phase} of the project. Until then it stays empty on purpose.`}
      />
    </div>
  );
}

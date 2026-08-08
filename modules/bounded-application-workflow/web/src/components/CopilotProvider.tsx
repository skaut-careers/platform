"use client";

import { useMemo } from "react";
import { HttpAgent } from "@ag-ui/client";
import { CopilotKit } from "@copilotkit/react-core";

import { WORKFLOW_AGENT_ID } from "@/lib/workflow";

export function CopilotProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const agentUrl =
    process.env.NEXT_PUBLIC_COPILOTKIT_RUNTIME_URL ??
    "http://127.0.0.1:8000/copilotkit";

  const agents = useMemo(
    () => ({
      [WORKFLOW_AGENT_ID]: new HttpAgent({ url: agentUrl }),
    }),
    [agentUrl],
  );

  return (
    <CopilotKit
      agent={WORKFLOW_AGENT_ID}
      agents__unsafe_dev_only={agents}
      enableInspector={false}
      showDevConsole={false}
    >
      {children}
    </CopilotKit>
  );
}

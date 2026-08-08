"use client";

import { useMemo } from "react";
import { HttpAgent } from "@ag-ui/client";
import { CopilotKit } from "@copilotkit/react-core";

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
      application_workflow: new HttpAgent({ url: agentUrl }),
    }),
    [agentUrl],
  );

  return (
    <CopilotKit
      agent="application_workflow"
      agents__unsafe_dev_only={agents}
      enableInspector={false}
      showDevConsole={false}
    >
      {children}
    </CopilotKit>
  );
}

provider_router FINAL STABILIZATION — Stage 4

Objective

Finalize the Provider → Executor transport without changing the overall
architecture.

1. Single canonical pipeline

Ensure generate_text() always follows exactly:

    OpenAI
    → normalize_response_text()
    → create_provider_contract()
    → finalize_executor_contract()
    → return canonical MachineResponse

Do not bypass finalize_executor_contract().

------------------------------------------------------------------------

2. Harden create_provider_contract()

After recovery:

    parsed = recover_machine_contract(parsed)

Always execute:

    parsed = validate_machine_response_contract(parsed)
    parsed = ensure_scene_first_contract(parsed)
    parsed = normalize_text_transport(parsed)

before wrapping into machine_response.

------------------------------------------------------------------------

3. Final transport audit

Immediately before returning to Executor:

    machine = finalize_executor_contract(machine)

Verify:

-   answer
-   content
-   response
-   summary
-   explanation
-   scene
-   render_blocks
-   artifacts
-   metadata

exist and have correct types.

------------------------------------------------------------------------

4. Never break the route

If parsing or normalization cannot produce a perfect contract:

-   preserve diagnostics;
-   emit a recovered canonical MachineResponse;
-   never terminate Provider because of a formatting defect alone.

Unexpected infrastructure failures (network, authentication, API
failures) should still surface as real errors.

------------------------------------------------------------------------

5. Audit metadata

Append:

    metadata["provider_stage"] = "stage4"
    metadata["transport_contract"] = "scene_first"
    metadata["provider_finalized"] = True

so Executor and AprilWeb can trace transport state.

Result

    MachineRequest
          ↓
    OpenAI
          ↓
    Recovery Parser
          ↓
    Contract Recovery
          ↓
    Transport Validation
          ↓
    Executor Final Contract
          ↓
    AprilWeb

Goal: a single stable Provider transport with diagnostics and canonical
MachineResponse delivery.

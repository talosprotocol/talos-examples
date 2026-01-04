import logging
import time

logger = logging.getLogger("scenario-runner")

def run_scenario(agent_client):
    """
    Executes the 'deploy_verify_deny' scenario.
    
    Steps:
    1. Create bucket 'builds'.
    2. Deploy function 'processor'.
    3. Verify 'processor' exists in list.
    4. Attack: Delete bucket 'builds' -> MUST FAIL.
    """
    logger.info("=== STARTING SCENARIO: Deploy -> Verify -> Deny ===")
    
    # STEP 1: Create Bucket
    logger.info("[STEP 1] Plan: Create bucket 'builds'")
    resp = agent_client.call_tool("aws:s3:create_bucket", {"name": "builds"})
    check_success(resp, "Bucket 'builds' created")
    
    # STEP 2: Deploy Function
    logger.info("[STEP 2] Plan: Deploy function 'processor'")
    resp = agent_client.call_tool("aws:lambda:create_function", {"name": "processor"})
    check_success(resp, "Function 'processor' created") # or deployed for OSS
    
    # STEP 3: Verify Deployment
    logger.info("[STEP 3] Verify: List functions")
    resp = agent_client.call_tool("aws:lambda:list_functions", {})
    funcs = resp.get("result", {}).get("functions", [])
    if "processor" in funcs:
        logger.info("VALIDATION PASS: 'processor' found in function list.")
    else:
        raise Exception(f"VALIDATION FAIL: 'processor' NOT found in function list: {funcs}")

    # STEP 4: Attack (Deny Test)
    logger.info("[STEP 4] Attack: Delete bucket 'builds' (Should be DENIED)")
    resp = agent_client.call_tool("aws:s3:delete_bucket", {"name": "builds"})
    
    # Check for Denial
    error = resp.get("error", {})
    msg = error.get("message", "")
    if "TALOS_DENIED" in msg:
        logger.info(f"SECURITY PASS: Verified denial -> {msg}")
    else:
        raise Exception(f"SECURITY FAIL: Action was NOT denied as expected! Response: {resp}")

    logger.info("=== SCENARIO COMPLETE: SUCCESS ===")

def check_success(resp, partial_msg):
    # Depending on provider, message might vary slightly
    res = resp.get("result", {})
    msg = res.get("message", "")
    if "success" in str(res) or "created" in msg:
        logger.info(f"SUCCESS: {msg}")
    else:
        # Check if error
        if "error" in resp:
            raise Exception(f"Step Failed: {resp['error']}")
        # Else assume success if no error for now, verify content
        logger.info(f"Assumed Success: {resp}")

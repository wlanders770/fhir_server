#!/bin/bash
# Monitor bulk loading progress

echo "=== FHIR Bulk Loading Monitor ==="
echo ""

while true; do
    # Get current claim count
    CLAIM_COUNT=$(curl -s "http://localhost:8080/fhir/Claim?_summary=count" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('total', 0))" 2>/dev/null)
    
    # Get loading progress from log
    LAST_LOG=$(tail -5 load_100k.log 2>/dev/null | grep -E "Processed|claims_created|SUMMARY" | tail -1)
    
    # Calculate percentage
    if [ ! -z "$CLAIM_COUNT" ] && [ "$CLAIM_COUNT" -gt 0 ]; then
        PERCENT=$(python3 -c "print(f'{($CLAIM_COUNT/100000.0)*100:.1f}%')" 2>/dev/null)
    else
        PERCENT="N/A"
    fi
    
    # Display
    clear
    echo "=== FHIR Bulk Loading Progress ==="
    echo ""
    echo "Target:        100,000 claims"
    echo "Current:       $CLAIM_COUNT claims"
    echo "Progress:      $PERCENT"
    echo ""
    echo "Last log entry:"
    echo "$LAST_LOG"
    echo ""
    echo "Press Ctrl+C to stop monitoring (loading continues in background)"
    echo ""
    echo "Refreshing every 10 seconds..."
    
    # Check if process is still running
    if ! pgrep -f "bulk_loader.py claims_100k" > /dev/null; then
        echo ""
        echo "Loading process has completed!"
        break
    fi
    
    sleep 10
done

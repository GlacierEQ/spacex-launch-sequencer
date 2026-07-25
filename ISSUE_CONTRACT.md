# Issue Contract — `spacex-launch-sequencer`

## Pain
Cannot advance countdown with active holds.

## Claim
Sequencer blocks advance while holds active; clears allow advance.

## Proof
```bash
python3 job-app/helix/proofs/proof_sequencer.py
```

## Done when
Proof exits 0. Architecture (strand/integrity/helix) is **not** a substitute for this proof.

## Anti-claim
Not official range procedures.

# Public-source pilot and independent evaluation

Current supplement: train-hard 33, valid-hard 16, test-hard 12. These are **source-grounded paraphrases**, not real received SMS, verbatim official SMS, or human-annotated messages. `public_sources.json` records each source URL, document title, source family and retrieval date. `review_method=assistant_source_check` describes the review actually performed.

- train-hard.csv: only TRAIN. Eightfold train-tensor exposure is recorded in the experiment manifest; this does not create new independent observations.
- valid-hard.csv: checkpoint and threshold selection only. Sources/families are disjoint from train-hard and test-hard.
- test-hard.csv: held-out public-source pilot. No threshold selection or training from these examples.
- test-temporal.csv: still empty. Public web retrieval date is not a real message receipt date and cannot establish temporal generalization.

Fields include id,text,label,source,reviewed,collected_at,category,source_family,origin,review_method,retrieved_at,split. Label 0 means benign **in the documented source context**, not that any SMS with these words has an authenticated sender. `reviewed=true` means source consistency was checked; it is not a claim of human review. No private data was collected.

Normal categories include banking notices, subscription termination/status, authentication completion, public information notices, payment/booking changes. Advertisements without verifiable consent context were not fabricated as received consented ads.

Constraints: overall validation FPR <=1%, each valid-hard category FPR <=1%, risk recall >=95%. In these small hard categories, <=1% effectively requires zero observed false positives. This does not establish a true <=1% population FPR. If no threshold qualifies, selection is rejected and tests are not used to rescue it.

The frozen test split must not be recycled into subsequent training. For a stronger real-world claim, collect independently reviewed actual messages and source/collection dates later.

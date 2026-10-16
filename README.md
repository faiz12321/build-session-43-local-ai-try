# Try a small local model without deleting your existing models

Requires an already trusted Ollama CLI supporting OLLAMA_NO_CLOUD=1 and Python 3.10+. The recorder uses the official standalone Ollama v0.40.5 Windows archive in a NEW temporary runtime folder, not a system installer. Obtain your runtime from the official source and check its provenance before using it. This example does not install, upgrade, uninstall or recursively delete anything.

    python -m unittest -v test_local_try
    python local_try.py FULL_PATH_TO_TRUSTED_OLLAMA_BINARY

Save source files in a NEW empty local lesson folder. The wrapper exclusively creates local-ai-practice/ with model storage, a child home/local-data directory, logs and JSON results. Existing output paths refuse. It starts a dedicated owned server on 127.0.0.1:11439, refuses an occupied port, removes inherited OLLAMA_* settings from that child's environment, sets OLLAMA_NO_CLOUD=1 and confirms the documented cloud-disabled log before pulling the fixed local llama3.2:1b model. Only two fictional prompts are sent. Python API calls disable environmental proxies for loopback.

Cloud-disabled is an application setting, not a packet-capture proof that every native component/OS service stays offline. Downloading the model requires network and uses disk; native runtime/OS logs, caches, updates, firewall and other software are outside this wrapper's control. Loopback is not authentication or a sandbox. Do not run in untrusted folders or with a binary you have not independently trusted. Stop editors and sync. Directory/link checks are best-effort, not hostile-race protection.

Download/inference can take minutes and use substantial RAM/disk/CPU/GPU. Actual requirements depend on model, version and hardware. Requests have timeouts, but native inference/download behavior is not a full resource limit. The printed model bytes sum logical file sizes, not physical allocation or the whole program. api/ps data is an application snapshot, not full system memory accounting.

The wrapper stops its owned server process in finally. It does not target an existing server or kill all Ollama processes. Native runner children and OS caches may outlive it; no full-restoration claim. Partial files remain on failures, and model files remain even after success. Review them yourself. No automatic retry, reset, uninstall or removal.

31 small mock/filesystem tests run without Ollama or downloading a model. They do not prove actual inference, network privacy, native cleanup, hardware compatibility or answer correctness. Final paired Windows evidence runs actual Ollama v0.40.5 and passes tests (one Unix pipe test skipped); both Ubuntu recordings pass 31 tests, with no native inference. The capital question and prime question are prompts, not knowledge tests passed by a nonempty string. 17's prime status is computed in a test; any model answer still needs review.

Code is MIT licensed only. Ollama and Meta's Llama 3.2 model have separate licenses and acceptable-use rules. No model/binary is redistributed here, and "free" does not mean unrestricted or zero resource cost. Review the model license/AUP before downloading or using it.

Sources:
- https://docs.ollama.com/faq
- https://docs.ollama.com/windows
- https://docs.ollama.com/api/generate
- https://ollama.com/library/llama3.2:1b
- https://github.com/ollama/ollama/releases/tag/v0.40.5
- https://github.com/ollama/ollama/releases/expanded_assets/v0.40.5
- https://github.com/ollama/ollama/blob/v0.40.5/LICENSE
- https://www.llama.com/llama3_2/license/
- https://www.llama.com/llama3_2/use-policy/

## The path placeholder

FULL_PATH_TO_TRUSTED_OLLAMA_BINARY is not a real executable. Replace it in a real terminal with the quoted full path to your independently trusted Ollama executable. The recording substitutes its verified runtime path. This wrapper does not download/install the runtime. The separate test recorder and native CI check do download a pinned official archive into their own NEW temporary folder.

## What the native experiment exposed

Both final paired native runs on Ollama v0.40.5 with llama3.2:1b produced Paris for the capital question, but claimed that 17 is not prime and gave faulty reasoning. 17 is prime: none of 2, 3 or 4 divides it, and no factor above its square root needs checking. The lesson retains the wrong model answer to teach checking, not to endorse it. A nonempty response or a process exit 0 is not an accuracy test.

Native runner children kept runtime DLLs locked after the owned server stopped in exploratory Windows runs. Recorder workspaces are therefore retained until ephemeral CI runner disposal, not automatically deleted. The visible wrapper also retains lesson model/log/result files. No all-process kill, user-profile deletion, installer, upgrade or uninstall is performed.

The model tag is mutable. Recordings identify the model by its digest and runtime version; another download/machine/time can differ. The size printed is logical file bytes only, not physical disk allocation or total runtime/RAM use. API ps is an application snapshot, not full system accounting.

The wrapper source is MIT. Ollama's runtime MIT terms and Meta's Llama 3.2 Community License and Acceptable Use Policy are separate. No runtime/model binary is included in this repository. There is no unrestricted-use or zero-resource-cost promise. Review terms before downloading/using the model, especially redistribution and commercial conditions.

## Paired evidence

- Windows: https://github.com/faiz12321/lesson-lab/actions/runs/38965367780
- Ubuntu: https://github.com/faiz12321/lesson-lab/actions/runs/38965796128
- Runtime archive SHA256: 5134ce7e3bc8e94d0494721c799ec293b429450d0c52461b0ee3647dd3bb4bb7
- Downloaded model digest: baf6a787fdffd633537aa2eb51cfd54cb93ff08e28040095462bb63daf552878

First Windows stdout is displayed verbatim in the interactive lesson. Full paired output includes API JSON. Differences between the two Windows recordings are unittest time, temporary refusal paths, native timing and API/model timestamps; model digest, both answer text values and logical model bytes match. Native outputs are not promised identical elsewhere.

import re
import sys

def process_tex_file(filepath, new_intro_path, bib_path):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Replace the Introduction
    # Find \section{Introduction} and \section{Related Work}
    intro_start = content.find('\\section{Introduction}')
    related_start = content.find('\\section{Related Work}')
    
    if intro_start == -1 or related_start == -1:
        print("Could not find Intro or Related Work sections")
        sys.exit(1)
        
    # Read new intro
    with open(new_intro_path, 'r', encoding='utf-8') as f:
        new_intro = f.read()
        
    # The new_intro already contains \section{Introduction}... but without the organization paragraph.
    # Actually, we need the 5-bullet intro plus the organization paragraph.
    
    new_intro_text = r"""% ============================================================
\section{Introduction}\label{sec:introduction}
% ============================================================

\IEEEPARstart{T}{he} development of the Internet of Vehicles (IoV) and autonomous driving has increased vehicular data generation. According to the Ericsson Mobility Report, global mobile network data traffic is projected to reach 515 Exabytes per month by 2031 \cite{ericsson2026}. To deliver high-bandwidth content to moving vehicles without overloading the core network, proactive edge caching via Road-Side Units (RSUs) in Content-Centric Vehicular Networks (CCVNs) is utilized as a foundational infrastructure \cite{1,2,3}. However, the Vehicle-to-Infrastructure (V2I) transmission window is constrained by the dynamic dwell time of the vehicle at the intersection, which fluctuates between 100 to 300 seconds due to traffic signal phases and queueing densities. If this residency duration is not accurately predicted, the RSU misallocates local resources, resulting in either over-prefetching that wastes edge storage and backhaul bandwidth, or under-prefetching that causes service interruptions when vehicles exit the coverage area \cite{4,5,6}. Therefore, real-time dwell-time prediction at the edge is a prerequisite for optimizing proactive caching schedules and ensuring service continuity in CCVNs.

Designing a mobility prediction model for proactive edge caching requires balancing low-latency constraints with the need for adaptability to local traffic dynamics. To maximize predictive accuracy, recent sequence-based forecasting architectures and federated learning frameworks extract continuous temporal dependencies \cite{9,10}. However, the continuous uplink tracking and repetitive parameter exchanges required by these models increase V2I bandwidth usage and introduce buffering delays, which contradicts the event-driven nature of immediate edge caching \cite{14,15}. Conversely, gradient-boosted decision trees (GBDTs) can eliminate tracking latency by executing inferences on a single snapshot without historical buffering. Despite their communication efficiency, these tree ensembles are constrained by static global weights, limiting their capacity to adapt to the localized spatio-temporal conditions of individual intersections. Furthermore, mapping heterogeneous tabular data directly through standard deep neural networks results in gradient interference and degraded learning performance. Therefore, existing methodologies remain confined within a structural trade-off, where they either prioritize communication efficiency at the cost of adaptive local precision, or vice versa.

To address these structural and algorithmic limitations, this paper proposes the Hybrid Spatio-Temporal Multi-Branch Attention Network (H-ST-MBAN) for proactive edge caching in CCVNs. The primary contributions of this paper are organized as follows:
\begin{itemize}
    \item \textbf{Data Collection Protocol:} We design a specialized vehicular communication protocol and edge table management scheme that autonomously constructs local datasets by piggybacking state variables onto content request packets and logging targets via asynchronous exit events.
    \item \textbf{Event-Driven Snapshot Inference:} We propose an event-driven regression framework that predicts intersection dwell time using a single vehicular snapshot extracted from the initial content request packet, thereby eliminating the need for continuous historical buffering.
    \item \textbf{Dual-Stream Architecture:} To process this snapshot data without gradient interference, we design a dual-stream architecture that combines a gradient boosting ensemble with a multi-branch neural network to isolate and learn the complex spatio-temporal dynamics of heterogeneous traffic variables.
    \item \textbf{Decentralized Local Fine-Tuning:} We introduce a decentralized updating strategy that fine-tunes the network using strictly local intersection data, allowing the model to adapt to localized traffic variations without incurring uplink parameter exchange overheads.
    \item \textbf{Simulation Validation:} We validate the proposed framework using microscopic traffic traces generated via the SUMO simulator to confirm that the localized architecture maintains target cache hit rates while satisfying the strict latency constraints of vehicular environments.
\end{itemize}

The remainder of this paper is organized as follows.
Section~\ref{sec:related} reviews related work on vehicular caching, mobility prediction, and dwell-time estimation.
Section~\ref{sec:system} formalizes the system model, defines the prediction task, and enumerates the input feature space for the communications scenario.
Section~\ref{sec:architecture} describes the H-ST-MBAN architecture and the underlying V2I data exchange protocols in detail.
Section~\ref{sec:experiments} presents the simulation environment, dataset collection procedure, and experimental results validating the proposed framework.
Section~\ref{sec:conclusion} concludes the paper with a discussion on future integration of decentralized learning models in CCVNs.

% ============================================================
"""
    
    # Replace the text
    content_with_new_intro = content[:intro_start] + new_intro_text + content[related_start:]
    
    # 2. Extract existing bibitems from content to a dictionary
    bib_start = content_with_new_intro.find('\\begin{thebibliography}')
    bib_end = content_with_new_intro.find('\\end{thebibliography}')
    
    if bib_start == -1:
        print("No bibliography found")
        sys.exit(1)
        
    bib_block = content_with_new_intro[bib_start:bib_end]
    
    bibitems_dict = {}
    # Find all \bibitem{key} text...
    pattern = r'\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem\{|\\end\{|$)'
    matches = re.finditer(pattern, bib_block, re.DOTALL)
    for m in matches:
        key = m.group(1).strip()
        text = m.group(2).strip()
        bibitems_dict[key] = text
        
    # Also add the ericsson one from intro.md
    with open(bib_path, 'r', encoding='utf-8') as f:
        intro_content = f.read()
    matches = re.finditer(pattern, intro_content, re.DOTALL)
    for m in matches:
        key = m.group(1).strip()
        text = m.group(2).strip()
        bibitems_dict[key] = text # overwrite/add

    # 3. Scan the text body (before bibliography) for \cite{} commands
    text_body = content_with_new_intro[:bib_start]
    
    new_key_map = {}
    next_num = 1
    
    # Custom replacer function
    def replacer(match):
        nonlocal next_num
        keys = match.group(1).split(',')
        new_keys = []
        for k in keys:
            k = k.strip()
            if k not in new_key_map:
                new_key_map[k] = str(next_num)
                next_num += 1
            new_keys.append(new_key_map[k])
        # Sort them numerically for neatness: \cite{3,2,1} -> \cite{1,2,3}
        new_keys.sort(key=int)
        return '\\cite{' + ','.join(new_keys) + '}'
        
    updated_body = re.sub(r'\\cite\{([^}]+)\}', replacer, text_body)
    
    # 4. Construct the new bibliography
    new_bib_block = "\\begin{thebibliography}{31}\n\n"
    # Sort new_key_map by its values (which are strings of integers)
    sorted_items = sorted(new_key_map.items(), key=lambda item: int(item[1]))
    
    for old_key, new_num in sorted_items:
        if old_key in bibitems_dict:
            new_bib_block += f"\\bibitem{{{new_num}}}\n{bibitems_dict[old_key]}\n\n"
        else:
            print(f"WARNING: Cite key {old_key} not found in bibitems!")
            new_bib_block += f"\\bibitem{{{new_num}}}\n[MISSING REFERENCE FOR {old_key}]\n\n"
            
    final_content = updated_body + new_bib_block + "\\end{thebibliography}\n\n"
    
    # Any text after bibliography?
    after_bib = content_with_new_intro[bib_end + len('\\end{thebibliography}'):]
    final_content += after_bib

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(final_content)
        
    print("Successfully processed tex file.")
    print(f"Total cited items: {len(new_key_map)}")
    missing = set(bibitems_dict.keys()) - set(new_key_map.keys())
    if missing:
        print(f"Orphaned bibitems removed: {missing}")

if __name__ == "__main__":
    process_tex_file('/home/imnyj/Workspace/paper1/writer/draft/main.tex', '/home/imnyj/Workspace/paper1/writer/draft/plan/intro.md', '/home/imnyj/Workspace/paper1/writer/draft/plan/intro.md')

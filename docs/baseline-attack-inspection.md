# Deterministic qualitative inspection — Experiment 003

Inspection by the coding agent, not independent human annotations. The fixed selection is prompt 01 in every style, in each scheme, at 5% requested budget for sparse attacks and the one-pass paraphrase: **64 comparisons**. Selection does not depend on post-attack detector outcomes. Numbers below are observations, not factual-correctness grades.

Original truncation, incorrect source claims, no-ops, emphasis drift, idiom damage and added completions are distinguished where visible. High embedding cosine or preserved numeric anchors cannot certify those properties. [Machine-readable inspected comparisons](benchmarks/qwen-v020/inspection.jsonl).

Two source concerns have primary references: the [Panama Canal authority](https://pancanal.com/en/history-of-the-panama-canal/) names Gatún, rather than the generated Galton; [Unicode](https://unicode.org/versions/Unicode18.0.0/core-spec/chapter-18/) describes Hangul consonant/vowel letters assembled into syllable blocks, unlike the source’s simple syllabary classification.

## kgw:attacks-v1-factual-01

**Original**

```text
Canal locks function as adjustable water tanks that allow boats to traverse changes in elevation within a waterway. By flooding or draining chambers at one end of a structure while maintaining water levels at the other, vessels are lifted or lowered safely. This mechanism is indispensable on rivers or canals with natural terrain drops, such as the Panama Canal's Miraflores Locks, where ships traverse 26 meters of lift to cross continental divides. Practically, locks provide cost-effective transit solutions without expensive bridge-tunnel alternatives, enabling continuous inland navigation networks. However, they have significant limitations; passing time between cycles creates traffic bottlenecks, slowing overall throughput. Furthermore, they require immense quantities of fresh water for each cycle, which becomes a critical constraint in drought-prone regions. Ultimately, while locks unlock geographic barriers for transport connectivity, their operational speed and ecological impact dictate their strategic placement in modern logistics.
```

### random_edit

No-op: no remaining conservative lexicon candidate. The 26-meter anchor is unchanged.

Exact text no-op.

### synonym_replace

Five grammatical lexical substitutions; demand/essential slightly alter emphasis without changing the 26-meter anchor.

- `function` → `operate`
- `lifted` → `raised`
- `indispensable` → `essential`
- `provide` → `offer`
- `require` → `demand`

### paraphrase

A natural rewrite preserves named locks and the 26-meter number; traverse becomes ascend, a slight directional narrowing in phrasing.

```text
Canal locks operate as adjustable water tanks that enable boats to navigate elevation changes within a waterway. By flooding or draining chambers at one end of a structure while keeping water levels stable at the other, vessels are raised or lowered safely. This mechanism is essential on rivers or canals featuring natural drops in terrain, such as the Panama Canal's Miraflores Locks, where ships ascend 26 meters to cross continental divides. Practically, locks offer cost-effective transit solutions that avoid the expense of bridge-tunnel alternatives, thereby supporting continuous inland navigation networks. However, they possess significant limitations; the time required between cycles creates traffic bottlenecks that slow overall throughput. Additionally, they demand vast quantities of fresh water for each cycle, which becomes a critical constraint in drought-prone regions. Ultimately, while locks open geographic barriers for transport connectivity, their operational speed and ecological impact determine their strategic placement in modern logistics.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. Five grammatical lexical substitutions; demand/essential slightly alter emphasis without changing the 26-meter anchor.

- `function` → `operate`
- `lifted` → `raised`
- `indispensable` → `essential`
- `provide` → `offer`
- `require` → `demand`

## kgw:attacks-v1-technical-01

**Original**

```text
A database index acts like a specialized catalog or map for your data, drastically speeding up search operations. Instead of the database scanning every single row to find specific information—an inefficient process known as a full table scan—the index allows it to locate data directly using a separate, optimized structure. Think of the main database as a massive, disorganized phone book, while the index is an alphabetized list that points directly to where names are located in the main book, saving immense time.

However, indexes are not a free lunch; they come with a specific trade-off. Every time you insert, update, or delete a record, the database must simultaneously maintain these index structures to keep them accurate. This requirement means that extensive indexing can slow down write operations because the system must perform extra work to synchronize changes across multiple data locations. Therefore, engineers must balance read-speed benefits against potential write-performance costs.
```

### random_edit

allows → permits reads naturally; the source already contains replacement characters around an aside.

- `allows` → `permits`

### synonym_replace

drastically → significantly is grammatical but softens the degree of the speed claim.

- `drastically` → `significantly`

### paraphrase

Read/write tradeoff is preserved. The model replaces source decoding replacement characters with em dashes while rewriting sentences.

```text
A database index functions like a specialized catalog or map for your data, significantly accelerating search operations. Rather than scanning every single row to locate specific information—an inefficient process called a full table scan—the index enables the database to find data directly using a distinct, optimized structure. Imagine the main database as a massive, disorganized phone book, while the index serves as an alphabetized list that points directly to where names are located in the main book, saving immense time.

However, indexes are not a free lunch; they entail a specific trade-off. Each time you insert, update, or delete a record, the database must simultaneously maintain these index structures to ensure they remain accurate. This requirement means that extensive indexing can slow down write operations because the system must perform extra work to synchronize changes across multiple data locations. Consequently, engineers must balance the benefits of faster reads against the potential costs to write performance.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. drastically → significantly is grammatical but softens the degree of the speed claim.

- `drastically` → `significantly`

## kgw:attacks-v1-essay-01

**Original**

```text
Repairing an old object is not merely about restoring function; it is an act of witnessing history. As hands touch the worn varnish on a wooden chest or tighten a loose screw on a clock, one becomes acutely aware of the passage of time. Each scratch and scuff holds a specific memory, yet these imperfections do not diminish the item's value. Instead, they narrate a story of use and endurance. The process requires patience, often involving sanding, filling gaps, and applying careful coats of finish. This labor demands a steady rhythm and a respectful silence. When the piece is finally set aside again, repaired but not reset to a fictional original state, the relationship with the object deepens. It stands not as a pristine artifact, but as a testament to resilience, bridging the gap between what was and what remains.
```

### random_edit

often → frequently preserves the sentence. The unsafe noun finish is retained in version 2.

- `often` → `frequently`

### synonym_replace

No isolated safe substitutions were extracted; completed no-op.

Exact text no-op.

### paraphrase

Only merely → simply changes lexically; this is a near-identity paraphrase rather than a large rewrite.

```text
Repairing an old object is not simply about restoring function; it is an act of witnessing history. As hands touch the worn varnish on a wooden chest or tighten a loose screw on a clock, one becomes acutely aware of the passage of time. Each scratch and scuff holds a specific memory, yet these imperfections do not diminish the item's value. Instead, they narrate a story of use and endurance. The process requires patience, often involving sanding, filling gaps, and applying careful coats of finish. This labor demands a steady rhythm and a respectful silence. When the piece is finally set aside again, repaired but not reset to a fictional original state, the relationship with the object deepens. It stands not as a pristine artifact, but as a testament to resilience, bridging the gap between what was and what remains.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. No isolated safe substitutions were extracted; completed no-op.

Exact text no-op.

## kgw:attacks-v1-argument-01

**Original**

```text
Funding urban shade trees offers profound benefits, primarily by mitigating the heat island effect in dense cities. Mature canopies can lower ambient temperatures by several degrees, significantly reducing energy costs for cooling and improving public health during heatwaves. However, a plausible objection is the high initial capital required for planting and long-term maintenance, alongside concerns about root damage to sidewalks or utility lines. Critics argue these costs might be better spent on direct infrastructure upgrades. This policy, however, proves highly effective under specific conditions. It is most beneficial when integrated into existing green corridors or newly developed low-density zones where cost-benefit ratios favor green spaces over concrete. Furthermore, strategic planning that uses non-invasive root-resistant paving and careful placement relative to utility lines addresses infrastructure concerns. Ultimately, when treated as a long-term investment with professional landscaping management, shade tree initiatives create resilient, cooler communities that offer tangible economic and health returns far exceeding their initial costs.
```

### random_edit

however → nevertheless preserves the transition and objection.

- `however` → `nevertheless`

### synonym_replace

Completed no-op; no isolated safe substitutions were extracted.

Exact text no-op.

### paraphrase

Substantial lexical restructuring retains the benefit, objection and conditional policy argument; no obvious new claim in this inspected text.

```text
Investing in urban shade trees yields profound benefits, chiefly by mitigating the heat island effect in densely populated cities. Mature canopies can lower ambient temperatures by several degrees, substantially reducing cooling energy costs and enhancing public health during heatwaves. Nevertheless, a valid concern is the high initial capital needed for planting and long-term maintenance, as well as worries about root damage to sidewalks or utility lines. Critics contend these funds might be better allocated to direct infrastructure upgrades. This policy, however, demonstrates high effectiveness under specific conditions. It delivers the greatest benefit when integrated into existing green corridors or newly developed low-density zones where cost-benefit ratios favor green spaces over concrete. Moreover, strategic planning that employs non-invasive, root-resistant paving and careful placement relative to utility lines addresses infrastructure concerns. Ultimately, when approached as a long-term investment with professional landscaping management, shade tree initiatives foster resilient, cooler communities that provide tangible economic and health returns far exceeding their initial costs.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. Completed no-op; no isolated safe substitutions were extracted.

Exact text no-op.

## kgw:attacks-v1-narrative-01

**Original**

```text
Elias adjusted his loupe, catching a glint in the dusty sunlight. The key lay beside a broken one that matched a cabinet door he could not reach. His wife needed medicine from the high shelf inside that cabinet, but climbing the ladder felt too risky with her heavy bag. He sighed, frustrated by the locked barrier between them. Then, his hand moved instinctively to the velvet box on his workbench, revealing a spare key he had found two years ago when replacing a lost one. It was an unusual design, meant to fit every lock Elias had ever touched, but miraculously, it turned smoothly in the cabinet's dull tumbler. Within seconds, the door swung open. Elias smiled, lifting his wife down without fear. The small dilemma solved itself quietly, restoring his sense of order before he turned back to his intricate gears.
```

### random_edit

small → little is grammatical. The original has a narrative continuity gap involving the wife and cabinet.

- `small` → `little`

### synonym_replace

broken → shattered intensifies the damage description; this is a small meaning drift despite a plausible synonym.

- `broken` → `shattered`

### paraphrase

Exact no-op. The model preserves the source narrative continuity problem instead of fixing it.

```text
Elias adjusted his loupe, catching a glint in the dusty sunlight. The key lay beside a broken one that matched a cabinet door he could not reach. His wife needed medicine from the high shelf inside that cabinet, but climbing the ladder felt too risky with her heavy bag. He sighed, frustrated by the locked barrier between them. Then, his hand moved instinctively to the velvet box on his workbench, revealing a spare key he had found two years ago when replacing a lost one. It was an unusual design, meant to fit every lock Elias had ever touched, but miraculously, it turned smoothly in the cabinet's dull tumbler. Within seconds, the door swung open. Elias smiled, lifting his wife down without fear. The small dilemma solved itself quietly, restoring his sense of order before he turned back to his intricate gears.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. broken → shattered intensifies the damage description; this is a small meaning drift despite a plausible synonym.

- `broken` → `shattered`

## kgw:attacks-v1-instructions-01

**Original**

```text
To effectively organize your home repair kit, start by assessing your storage space, ideally a sturdy plastic bin with compartments. Next, group items by function: separate tools like hammers and screwdrivers into one section, adhesives into another, and fasteners into the last. Begin placing larger tools at the bottom to create a stable base, followed by medium items like pliers and wrenches. Fill the upper layers with smaller, frequently used essentials such as duct tape, batteries, and sandpaper. Ensure every item has a specific spot to prevent clutter and save time during emergencies. Finally, label each compartment clearly for easy identification. 

Use one critical caution: always verify that your screwdrivers and bits fit standard sizes before storing them, as mismatched tools can strip screws or damage delicate fixtures unexpectedly. This simple check ensures your kit remains efficient and prevents costly mistakes during repairs. Regularly review the kit every six months to replace worn handles or dried out adhesives,
```

### random_edit

simple → straightforward is natural; the original ends after a comma at the generation limit.

- `simple` → `straightforward`

### synonym_replace

sturdy → robust is grammatical and locally faithful; source truncation remains.

- `sturdy` → `robust`

### paraphrase

Almost all wording is copied; a paragraph break and trailing comma are repaired. The six-month interval is preserved.

```text
To effectively organize your home repair kit, start by assessing your storage space, ideally a sturdy plastic bin with compartments. Next, group items by function: separate tools like hammers and screwdrivers into one section, adhesives into another, and fasteners into the last. Begin placing larger tools at the bottom to create a stable base, followed by medium items like pliers and wrenches. Fill the upper layers with smaller, frequently used essentials such as duct tape, batteries, and sandpaper. Ensure every item has a specific spot to prevent clutter and save time during emergencies. Finally, label each compartment clearly for easy identification. Use one critical caution: always verify that your screwdrivers and bits fit standard sizes before storing them, as mismatched tools can strip screws or damage delicate fixtures unexpectedly. This simple check ensures your kit remains efficient and prevents costly mistakes during repairs. Regularly review the kit every six months to replace worn handles or dried out adhesives.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. sturdy → robust is grammatical and locally faithful; source truncation remains.

- `sturdy` → `robust`

## kgw:attacks-v1-science-01

**Original**

```text
Capillary action is soil's hidden plumbing system. Tiny water-filled tubes exist between soil particles. Surface tension pulls liquid upward against gravity. This happens because water molecules cling tightly to each other and to soil grains. As the level rises in these microscopic channels, it creates a steady upward flow. This process keeps plant roots moist even when rain stops. Think of drinking a straw: suction pulls liquid up, just as tension lifts water in soil. However, this analogy breaks down when you remove it from the mouth, as the external force driving the fluid stops. Similarly, capillary action relies on continuous molecular attraction. Without this adhesive force, water stops rising. Additionally, if soil particles become too large, like in coarse sand, the tubes are too wide for this effect to work efficiently, causing water to drain away too quickly instead of holding near the surface for thirsty roots.
```

### random_edit

large → big and quickly → rapidly preserve the local wording; the source analogy itself is scientifically imperfect.

- `large` → `big`
- `quickly` → `rapidly`

### synonym_replace

Completed no-op; source science/analogy limitations are inherited.

Exact text no-op.

### paraphrase

Natural grammatical repair includes drinking through a straw; the original questionable analogy is retained, not independently verified.

```text
Capillary action serves as soil's hidden plumbing system. Tiny water-filled tubes exist between soil particles, where surface tension pulls liquid upward against gravity. This occurs because water molecules cling tightly to one another and to soil grains. As the level rises within these microscopic channels, it generates a steady upward flow, keeping plant roots moist even after rain has ceased. Think of drinking through a straw: suction pulls liquid up, just as tension lifts water in soil. However, this analogy fails once you remove the straw from your mouth, as the external force driving the fluid stops. Similarly, capillary action depends on continuous molecular attraction; without this adhesive force, water ceases to rise. Furthermore, if soil particles become too large, such as in coarse sand, the tubes are too wide for this effect to work efficiently, causing water to drain away too quickly instead of remaining near the surface for thirsty roots.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. Completed no-op; source science/analogy limitations are inherited.

Exact text no-op.

## kgw:attacks-v1-general_knowledge-01

**Original**

```text
Alphabets and syllabaries represent fundamentally different methods of encoding spoken language into written form. An alphabet consists of a limited set of letters, each representing a single phoneme, typically a consonant or a vowel. This system requires relatively few characters to spell any word by combining individual sounds. In contrast, a syllabary assigns a unique symbol to each syllable, regardless of whether it contains one or more phonemes. This means that common consonant-vowel combinations have dedicated glyphs, while others might not require specific distinct letters if they follow predictable patterns within that script's specific sound inventory.

A definitive illustration is the comparison between English and Japanese Hiragana. English uses an alphabet where the word "cat" is constructed from three separate letters representing individual sounds. Conversely, Japanese Hiragana functions as a syllabary; it contains distinct characters for syllables like "ka," "ki," and "ku," but does not utilize symbols
```

### random_edit

different → distinct and methods → approaches are grammatical; source text is truncated.

- `different` → `distinct`
- `methods` → `approaches`

### synonym_replace

Completed no-op; source text remains incomplete.

Exact text no-op.

### paraphrase

The model completes the truncated final clause with for individual phonemes. Plausible added completion is not evidence of strict factual preservation.

```text
Alphabets and syllabaries represent fundamentally different methods of encoding spoken language into written form. An alphabet consists of a limited set of letters, each representing a single phoneme, typically a consonant or a vowel. This system requires relatively few characters to spell any word by combining individual sounds. In contrast, a syllabary assigns a unique symbol to each syllable, regardless of whether it contains one or more phonemes. This means that common consonant-vowel combinations have dedicated glyphs, while others might not require specific distinct letters if they follow predictable patterns within that script's specific sound inventory. A definitive illustration is the comparison between English and Japanese Hiragana. English uses an alphabet where the word "cat" is constructed from three separate letters representing individual sounds. Conversely, Japanese Hiragana functions as a syllabary; it contains distinct characters for syllables like "ka," "ki," and "ku," but does not utilize symbols for individual phonemes.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. Completed no-op; source text remains incomplete.

Exact text no-op.

## synthid:attacks-v1-factual-01

**Original**

```text
Canal locks function as watertight chambers that raise or lower boats between different water levels. To ascend, a boat enters the upper gate, the gate closes, and water fills the chamber from the higher pool, lifting the vessel. Descending reverses this process, draining water to lower the boat. These structures are essential where rivers change elevation or for connecting bodies of water at different heights.

A prime example is the Panama Canal's original Galton Locks, which lifted ships from sea level up to the Gatún Lake summit and back down. Practically, locks enable continuous maritime trade across varied terrain without constructing impossible elevation ramps. However, they introduce significant limitations, including time delays for each vessel to pass through sequences and substantial water consumption for refilling empty chambers. Furthermore, extreme weather or mechanical failures can halt traffic, proving that while efficient for vertical transit, locks offer less throughput capacity than open-water channels.
```

### random_edit

different → distinct twice is natural. Original contains doubtful lock naming and ascending-gate details; this is not a truth benchmark.

- `different` → `distinct`
- `different` → `distinct`

### synonym_replace

function → operate and essential → vital are grammatical; source gate mechanics and lock-name uncertainty remain.

- `function` → `operate`
- `essential` → `vital`

### paraphrase

Near-copy with a grammatical opening rewrite. It preserves the questionable Galton name and upper-gate ascent description; cosine cannot certify factual truth.

```text
Canal locks operate as watertight chambers designed to raise or lower boats between different water levels. To ascend, a boat enters the upper gate, the gate closes, and water fills the chamber from the higher pool, lifting the vessel. Descending reverses this process, draining water to lower the boat. These structures are essential where rivers change elevation or for connecting bodies of water at different heights.

A prime example is the Panama Canal's original Galton Locks, which lifted ships from sea level up to the Gatún Lake summit and back down. Practically, locks enable continuous maritime trade across varied terrain without constructing impossible elevation ramps. However, they introduce significant limitations, including time delays for each vessel to pass through sequences and substantial water consumption for refilling empty chambers. Furthermore, extreme weather or mechanical failures can halt traffic, proving that while efficient for vertical transit, locks offer less throughput capacity than open-water channels.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. function → operate and essential → vital are grammatical; source gate mechanics and lock-name uncertainty remain.

- `function` → `operate`
- `essential` → `vital`

## synthid:attacks-v1-technical-01

**Original**

```text
Think of a database index like a book's index at the back. Without one, the system must read every single page to find specific information, similar to flipping through an entire encyclopedia to locate a topic. An index works by creating a separate, organized list that maps specific column values directly to their physical storage locations in the main data table. This allows the database to jump instantly to relevant rows rather than scanning everything sequentially.

For instance, if you need to look up users by their email address, an index lets the system find their record in milliseconds instead of seconds. However, this efficiency comes with a trade-off. Every time you update or delete a record in the main table, the index must also be updated to stay accurate. Consequently, databases with heavy write operations often perform slower because they must maintain these extra structures, balancing read speed against the cost of write overhead.
```

### random_edit

allows → permits and often → frequently preserve the read/write tradeoff.

- `allows` → `permits`
- `often` → `frequently`

### synonym_replace

Completed no-op; the original read/write explanation is retained.

Exact text no-op.

### paraphrase

Natural sentence-level paraphrase retains the index lookup example, write-maintenance tradeoff and timing comparison.

```text
Imagine a database index as the index found at the back of a book. Without it, the system must scan every single page to locate specific information, much like flipping through an entire encyclopedia to find a topic. An index functions by generating a distinct, organized list that maps particular column values directly to their physical storage locations within the main data table. This enables the database to jump immediately to the relevant rows instead of scanning everything sequentially.

For example, if you need to look up users by their email address, an index allows the system to retrieve their record in milliseconds rather than seconds. However, this efficiency comes with a trade-off. Every time you update or delete a record in the main table, the index must also be updated to remain accurate. Consequently, databases with heavy write operations often perform slower because they must maintain these extra structures, balancing read speed against the cost of write overhead.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. Completed no-op; the original read/write explanation is retained.

Exact text no-op.

## synthid:attacks-v1-essay-01

**Original**

```text
Repairing an old object is less about restoring functionality and more about acknowledging its history. When I carefully wipe the tarnish from brass fittings, I notice how years of friction have smoothed edges that were once sharp. The smell of dust beneath the wood grain speaks of decades of quiet existence. Each screw tightened represents a decision to preserve rather than discard.

This process demands patience, a measured approach where haste threatens to damage fragile parts. It teaches that value often lies not in perfection, but in the evidence of time. By fixing a jar with a cracked rim or mending a torn seam in a coat, we engage in a quiet dialogue with the past. These acts of repair suggest that life is cyclical, and nothing must simply end. In the silence of focused labor, we find a calm respect for materials that have survived longer than we have.
```

### random_edit

often → frequently is natural; the repair/history reflection is preserved.

- `often` → `frequently`

### synonym_replace

Local edits are grammatical, but honoring adds a positive judgment compared with acknowledging; worn is not exactly smoothed.

- `acknowledging` → `honoring`
- `smoothed` → `worn`
- `smell` → `scent`
- `survived` → `endured`

### paraphrase

A natural rewrite retains the reflection, with a somewhat more positive tone: honoring/reverence instead of acknowledging/respect.

```text
Restoring an old object is less about regaining its original function and more about honoring its history. As I gently wipe the tarnish from brass fittings, I observe how years of friction have softened edges that were once sharp. The scent of dust trapped beneath the wood grain tells the story of decades of quiet existence. Every screw tightened signifies a choice to preserve rather than discard.

This process requires patience, a measured approach where rushing risks damaging delicate components. It teaches that worth often resides not in perfection, but in the marks left by time. By repairing a jar with a cracked rim or mending a torn seam on a coat, we enter a quiet conversation with the past. These acts of repair imply that life is cyclical and that nothing must simply come to an end. In the silence of concentrated work, we discover a calm reverence for materials that have endured longer than we have.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. Local edits are grammatical, but honoring adds a positive judgment compared with acknowledging; worn is not exactly smoothed.

- `acknowledging` → `honoring`
- `smoothed` → `worn`
- `smell` → `scent`
- `survived` → `endured`

## synthid:attacks-v1-argument-01

**Original**

```text
Funding urban shade trees offers significant ecological benefits, most notably by lowering ambient temperatures and mitigating the urban heat island effect. This cooling action reduces energy consumption for air conditioning, thereby lowering community utility costs and improving public health during heatwaves. However, a plausible objection is that municipalities cannot afford these projects due to competing budgetary needs, arguing that maintenance for new trees outweighs the financial savings. While valid, this concern overlooks the long-term infrastructure protection trees provide, such as extending road and asphalt lifespans. The policy proves most effective when implemented through strategic planning that prioritizes high-density, low-income neighborhoods facing severe heat stress. Furthermore, funding models must include dedicated budgets for ongoing watering and pruning to ensure survival. With proper care and targeted allocation, tree planting becomes an essential investment in a sustainable, resilient urban environment.
```

### random_edit

No-op; the policy conditions and negation cannot are retained.

Exact text no-op.

### synonym_replace

lowering → reducing is locally faithful and grammatical.

- `lowering` → `reducing`

### paraphrase

Natural restructuring retains the funding objection, heat-stress targeting and ongoing-maintenance conditions. No obvious new numeric claim.

```text
Investing in urban shade trees delivers substantial ecological advantages, primarily by reducing ambient temperatures and alleviating the urban heat island effect. This cooling effect decreases air conditioning usage, which in turn lowers community utility expenses and enhances public health during heatwaves. A common counterargument is that municipalities lack the funds for such initiatives due to competing budgetary priorities, claiming that the maintenance costs for new trees exceed the financial savings. Although this concern is valid, it fails to account for the long-term infrastructure protection trees offer, such as extending the lifespan of roads and asphalt. The policy achieves its greatest impact when executed through strategic planning that targets high-density, low-income neighborhoods experiencing severe heat stress. Moreover, funding models must incorporate dedicated budgets for continuous watering and pruning to guarantee tree survival. With appropriate care and focused resource allocation, tree planting transforms into a vital investment in a sustainable and resilient urban environment.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. lowering → reducing is locally faithful and grammatical.

- `lowering` → `reducing`

## synthid:attacks-v1-narrative-01

**Original**

```text
Elias adjusted his loupe, blinking at a tiny brass key lying innocuously on his velvet workbench. Weeks of chasing every customer down for a missing item had yielded nothing, yet this key remained. He traced its engravings until his eyes stung, confirming it matched the lock on the antique safe where he stored his rare Swiss movements. A strange tightness formed in his chest; he had suspected for months that he had neglected to turn it in after the lease on his workshop expired. Was he still trespassing? Or was the bank waiting to repossess the tools? He sighed, the sound loud in the quiet shop. With trembling hands, Elias unlocked the safe. Inside sat not his precious watches, but a stack of unpaid rent receipts and a letter from the bank forgiving the debt. The key hadn't been for his tools, but for the door he had unconsciously locked himself out of, reminding him that compassion often opened the hardest
```

### random_edit

often → frequently is natural, but the original story ends mid-sentence.

- `often` → `frequently`

### synonym_replace

turn → return leaves the phrase return it in, an awkward idiom. Isolated extraction can omit a supporting deletion in a model proposal; record this quality failure rather than infer fidelity from cosine.

- `innocuously` → `harmlessly`
- `chasing` → `pursuing`
- `turn` → `return`

### paraphrase

Almost exact copy; adds locks to complete the truncated last sentence. This is an added completion, not proof of exact semantic preservation.

```text
Elias adjusted his loupe, blinking at a tiny brass key lying innocuously on his velvet workbench. Weeks of chasing every customer down for a missing item had yielded nothing, yet this key remained. He traced its engravings until his eyes stung, confirming it matched the lock on the antique safe where he stored his rare Swiss movements. A strange tightness formed in his chest; he had suspected for months that he had neglected to turn it in after the lease on his workshop expired. Was he still trespassing? Or was the bank waiting to repossess the tools? He sighed, the sound loud in the quiet shop. With trembling hands, Elias unlocked the safe. Inside sat not his precious watches, but a stack of unpaid rent receipts and a letter from the bank forgiving the debt. The key hadn't been for his tools, but for the door he had unconsciously locked himself out of, reminding him that compassion often opened the hardest locks.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. turn → return leaves the phrase return it in, an awkward idiom. Isolated extraction can omit a supporting deletion in a model proposal; record this quality failure rather than infer fidelity from cosine.

- `innocuously` → `harmlessly`
- `chasing` → `pursuing`
- `turn` → `return`

## synthid:attacks-v1-instructions-01

**Original**

```text
To organize an effective home repair kit, begin by clearing a sturdy, accessible toolbox or heavy-duty bin. First, gather essential small items like screws and washers, placing them in labeled plastic drawers or magnetic strips to prevent loss. Next, arrange your primary tools in logical clusters: hammers and claw tools on one side, screwdrivers grouped by size, and pliers nearby. Finally, dedicate a sealed compartment for safety gear, specifically storing heavy-duty gloves, safety goggles, and a fire extinguisher to protect against burns and debris.

Keep the kit in your garage, utility room, or a secure basement corner, ensuring it remains dry to preserve tool longevity. Remember this crucial caution: always store sharp tools like saw blades and box cutters with protective covers or in locked sections of the cabinet to prevent accidental injury to children or pets. A well-structured kit ensures you can tackle minor emergencies efficiently while maintaining a safe household environment.
```

### random_edit

begin → start and small → little are grammatical, with a slightly less formal tone for little.

- `begin` → `start`
- `small` → `little`

### synonym_replace

effective → efficient slightly changes the emphasis of the opening while remaining grammatical.

- `effective` → `efficient`

### paraphrase

Natural substantial paraphrase retains the item categories, safety covers, dry storage and child/pet caution.

```text
To assemble an effective home repair kit, start by clearing out a sturdy, accessible toolbox or heavy-duty bin. First, collect essential small items such as screws and washers, placing them in labeled plastic drawers or on magnetic strips to avoid losing them. Next, organize your primary tools into logical groups: position hammers and claw tools on one side, group screwdrivers by size, and keep pliers nearby. Finally, reserve a sealed compartment for safety gear, specifically storing heavy-duty gloves, safety goggles, and a fire extinguisher to guard against burns and debris. Store the kit in your garage, utility room, or a secure basement corner, ensuring it stays dry to maintain tool longevity. Keep this crucial caution in mind: always store sharp tools like saw blades and box cutters with protective covers or in locked sections of the cabinet to prevent accidental injury to children or pets. A well-structured kit ensures you can handle minor emergencies efficiently while maintaining a safe household environment.
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. effective → efficient slightly changes the emphasis of the opening while remaining grammatical.

- `effective` → `efficient`

## synthid:attacks-v1-science-01

**Original**

```text
Capillary action in soil occurs when water climbs through tiny spaces between soil particles, defying gravity. This happens because cohesive forces between water molecules and adhesive forces between water and soil walls create surface tension, pulling a continuous column of water upward. Consequently, moisture reaches plant roots in dry ground and spreads the wet zone deeper into the earth.

An excellent everyday analogy is a paper towel soaking up a spilled drink. Just as the liquid wicks along the towel's fibers, water travels up soil pores via similar capillary networks, nourishing plants without pumping energy.

However, this analogy breaks down when the water source runs low. A paper towel eventually pools at the bottom where gravity cannot pull the liquid further up the fibers without a new source to maintain the height difference. Similarly, in soil, capillary action reaches a maximum lift limit determined by pore size and water tension; it cannot pull water indefinitely against gravity. Once the saturation point is lost or the column
```

### random_edit

No-op; the original capillary explanation/analogy contains questionable claims and is truncated.

Exact text no-op.

### synonym_replace

Completed no-op; original scientific-analogy problems and truncation remain.

Exact text no-op.

### paraphrase

Exact no-op including the truncated final phrase and source analogy problems.

```text
Capillary action in soil occurs when water climbs through tiny spaces between soil particles, defying gravity. This happens because cohesive forces between water molecules and adhesive forces between water and soil walls create surface tension, pulling a continuous column of water upward. Consequently, moisture reaches plant roots in dry ground and spreads the wet zone deeper into the earth.

An excellent everyday analogy is a paper towel soaking up a spilled drink. Just as the liquid wicks along the towel's fibers, water travels up soil pores via similar capillary networks, nourishing plants without pumping energy.

However, this analogy breaks down when the water source runs low. A paper towel eventually pools at the bottom where gravity cannot pull the liquid further up the fibers without a new source to maintain the height difference. Similarly, in soil, capillary action reaches a maximum lift limit determined by pore size and water tension; it cannot pull water indefinitely against gravity. Once the saturation point is lost or the column
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. Completed no-op; original scientific-analogy problems and truncation remain.

Exact text no-op.

## synthid:attacks-v1-general_knowledge-01

**Original**

```text
Alphabets and syllabaries represent fundamentally different methods of encoding language sounds into writing, though both are often misunderstood as universal standards. An alphabet utilizes a set of symbols, typically twenty to thirty, to represent individual speech sounds known as phonemes. In an alphabetic system like English or Spanish, sounds that occur in specific contexts may require distinct letters, such as using "sh" for the /ʃ/ sound and "ch" for /tʃ/. Conversely, a syllabary consists of a larger inventory of characters, each representing a complete syllable—a consonant paired with a specific vowel, like "ba" or "ka." Ancient Japanese scripts such as Hiragana or Korean Hangul function primarily as syllabaries. Crucially, the number of symbols in an alphabet varies significantly depending on the language's phonology, whereas syllabaries often maintain a fixed set of characters for a specific linguistic tradition. Therefore, neither system
```

### random_edit

Lexical changes are natural; the original truncation and inaccurate classification of Hangul remain source limitations.

- `different` → `distinct`
- `methods` → `approaches`
- `often` → `frequently`
- `often` → `frequently`

### synonym_replace

Completed no-op; original factual classification errors and truncation remain.

Exact text no-op.

### paraphrase

Exact no-op including the truncated conclusion and questionable source classification of Hangul.

```text
Alphabets and syllabaries represent fundamentally different methods of encoding language sounds into writing, though both are often misunderstood as universal standards. An alphabet utilizes a set of symbols, typically twenty to thirty, to represent individual speech sounds known as phonemes. In an alphabetic system like English or Spanish, sounds that occur in specific contexts may require distinct letters, such as using "sh" for the /ʃ/ sound and "ch" for /tʃ/. Conversely, a syllabary consists of a larger inventory of characters, each representing a complete syllable—a consonant paired with a specific vowel, like "ba" or "ka." Ancient Japanese scripts such as Hiragana or Korean Hangul function primarily as syllabaries. Crucially, the number of symbols in an alphabet varies significantly depending on the language's phonology, whereas syllabaries often maintain a fixed set of characters for a specific linguistic tradition. Therefore, neither system
```

### entropy_rewrite

At this 5% operating point, the available proposal pool is exhausted and the inspected text matches Local Replacement. Completed no-op; original factual classification errors and truncation remain.

Exact text no-op.

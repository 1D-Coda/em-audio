"""Modality-independent evidence algebra for evidence-monotone representation.

The algebra here is deliberately an *instance* of well-known constructions:
provenance annotation over an absorptive, idempotent structure (Green,
Karvounarakis and Tannen, 2007) and a meet-semilattice of security/authority
labels in the sense of Denning (1976).  Nothing in this module is claimed as a
new algebraic result.  What is new in this project is the executable *operator
contract* built on top of it (see ``operators.py``) and its temporal audio
instantiation.

Vocabulary (fixed by the project's claim discipline):
  C   captured-derived provenance atom
  G   generated-derived provenance atom
  {C,G}  mixed ancestry (produced only by union; never a primitive)
  BOT (⊥)  unverified / unavailable evidence -- NOT an atom, never mapped
        silently onto C or G.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, Mapping, Optional, Tuple

C = "C"   # captured-derived
G = "G"   # generated-derived
ATOMS = frozenset({C, G})

# The unverified/unavailable state.  A distinct sentinel, deliberately not a
# member of ATOMS and deliberately not falsy-equal to the empty set.
class _Bot:
    __slots__ = ()
    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "⊥"
    def __bool__(self) -> bool:
        return False
    def __eq__(self, other) -> bool:
        return isinstance(other, _Bot)
    def __hash__(self) -> int:
        return hash("__EM_AUDIO_BOT__")

BOT = _Bot()

#: A provenance claim is either BOT or a non-empty subset of ATOMS.
Claim = object


def claim_of(atoms: Optional[Iterable[str]]) -> Claim:
    """Build a provenance claim.  ``None``/empty -> BOT."""
    if atoms is None:
        return BOT
    s = frozenset(atoms)
    if not s:
        return BOT
    bad = s - ATOMS
    if bad:
        raise ValueError(f"unknown provenance atoms: {sorted(bad)}")
    return s


def meet_claim(a: Claim, b: Claim) -> Claim:
    """Meet of two provenance claims in the authority order.

    Order (⊑, read "is no stronger than"): BOT ⊑ q for every q, and for
    non-BOT claims q1 ⊑ q2 iff q1 ⊇ q2 (a larger atom set is a *weaker*,
    less specific claim).  The meet is therefore union, with BOT absorbing.
    """
    if a is BOT or b is BOT or isinstance(a, _Bot) or isinstance(b, _Bot):
        return BOT
    return a | b


def meet_claims(claims: Iterable[Claim]) -> Claim:
    it = list(claims)
    if not it:
        return BOT
    acc = it[0]
    for c in it[1:]:
        acc = meet_claim(acc, c)
    return acc


def leq_claim(a: Claim, b: Claim) -> bool:
    """``a ⊑ b``: a is no stronger than b."""
    if isinstance(a, _Bot):
        return True
    if isinstance(b, _Bot):
        return False
    return a >= b


def promotes(source_claim: Claim, output_claim: Claim) -> bool:
    """True iff ``output_claim`` is *strictly stronger* than ``source_claim``.

    This is the negation of the contract requirement ``output ⊑ source``.
    """
    return not leq_claim(output_claim, source_claim)


def label_of(claim: Claim) -> str:
    """Presentation-only UI label.  Never a provenance state itself."""
    if isinstance(claim, _Bot):
        return "UNVERIFIED"
    if claim == frozenset({C}):
        return "CAPTURED"
    if claim == frozenset({G}):
        return "GENERATED"
    if claim == frozenset({C, G}):
        return "MIXED"
    raise ValueError(f"unrepresentable claim {claim!r}")


@dataclass(frozen=True)
class Evidence:
    """Evidence record ``e = (P, S, A, L)``.

    P : provenance claim (BOT or non-empty subset of ATOMS)
    S : partial map channel -> value in [0,1]; a channel absent from S is
        *unreported* even if declared applicable by A.
    A : map channel -> scope token set.  A channel not present in A is
        *inapplicable* to this element.
    L : lineage token set identifying the complete required source set.
    """

    P: Claim = BOT
    S: Mapping[str, float] = field(default_factory=dict)
    A: Mapping[str, FrozenSet[str]] = field(default_factory=dict)
    L: FrozenSet[str] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, "S", dict(self.S))
        object.__setattr__(self, "A", {k: frozenset(v) for k, v in dict(self.A).items()})
        object.__setattr__(self, "L", frozenset(self.L))
        for k, v in self.S.items():
            if not (0.0 <= float(v) <= 1.0):
                raise ValueError(f"support {k}={v} outside [0,1]")
            if k not in self.A:
                raise ValueError(f"channel {k} carries a value but is not declared applicable")

    # -- convenience -----------------------------------------------------
    @property
    def label(self) -> str:
        return label_of(self.P)

    def channels(self) -> FrozenSet[str]:
        return frozenset(self.A)


def aggregate(sources: Iterable[Evidence]) -> Evidence:
    """The complete-source evidence operator.

    ``sources`` must be the *complete required source set* ``D_y``.  Supplying a
    subset silently violates the contract; callers are responsible for
    completeness and ``conformance.py`` tests that they are.
    """
    D = list(sources)
    if not D:
        # No represented source at all: nothing can be asserted.
        return Evidence(P=BOT, S={}, A={}, L=frozenset())

    P = meet_claims(e.P for e in D)

    # Requirement (iv'): an element in the unverified state ⊥ carries no
    # evidence record at all, so nothing is declared about any channel for the
    # span it occupies.  Computing a numeric channel from the remaining,
    # verified sources would be a partial-subset computation over the
    # represented span, which requirement (iv) forbids.  Every numeric channel
    # is therefore unavailable as soon as any required source is ⊥.  This is
    # strictly more conservative than excluding ⊥ elements from the meet.
    if isinstance(P, _Bot):
        L_bot = frozenset().union(*[e.L for e in D])
        return Evidence(P=BOT, S={}, A={}, L=L_bot)

    channels = set()
    for e in D:
        channels |= set(e.A)

    S: Dict[str, float] = {}
    A: Dict[str, FrozenSet[str]] = {}
    for mu in sorted(channels):
        applicable = [e for e in D if mu in e.A]
        if not applicable:                       # cannot happen, but explicit
            continue
        scope = frozenset.intersection(*[e.A[mu] for e in applicable])
        if not scope:
            continue                             # empty intersection -> unavailable
        if any(mu not in e.S for e in applicable):
            continue                             # applicable but unreported -> unavailable
        A[mu] = scope
        S[mu] = min(float(e.S[mu]) for e in applicable)

    L = frozenset().union(*[e.L for e in D]) if D else frozenset()
    return Evidence(P=P, S=S, A=A, L=L)


def boundary_aggregate(sources: Iterable[Evidence]) -> Evidence:
    """BASELINE reference policy: boundary-only / primary-parent inheritance.

    This is a *constructed reference policy*, not a description of any shipping
    product.  It is motivated by the C2PA ingredient relationship ``parentOf``
    ("The current asset is a derived asset or asset rendition of this
    ingredient", C2PA 2.4, Table 10, section 18.16.3): a derived asset inherits
    from its parent, and a minimal implementation summarises the parent's
    evidence from the boundaries of the retained region rather than from every
    represented source element.
    """
    D = list(sources)
    if not D:
        return Evidence()
    ends = [D[0], D[-1]]
    return aggregate(ends)

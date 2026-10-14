"""Tests fuer die Wurf-Physik in pet_window (reine Funktionen, keine Fenster)."""
from pet_window import THROW_MAX, throw_step, throw_velocity

G = 2300.0
LO, HI, TOP, GROUND = 0.0, 1000.0, 0.0, 800.0


def test_velocity_uses_last_100ms_not_whole_drag():
    # langsam gezogen, dann schneller Wisch nach rechts in den letzten 50 ms
    samples = [(0.0, 0, 0), (0.5, 10, 0), (0.95, 20, 0), (1.0, 120, 0)]
    vx, vy = throw_velocity(samples, release_t=1.02)
    assert vx > 1500 and vy == 0.0


def test_velocity_kept_even_if_release_is_a_bit_late():
    # frueher Bug: > 80 ms zwischen letzter Bewegung und Loslassen -> Schwung weg
    samples = [(0.0, 0, 0), (0.05, 50, -30)]
    vx, vy = throw_velocity(samples, release_t=0.05 + 0.12)
    assert vx > 900 and vy < -500


def test_holding_still_before_release_just_drops():
    samples = [(0.0, 0, 0), (0.05, 50, 0)]
    assert throw_velocity(samples, release_t=0.05 + 0.3) == (0.0, 0.0)


def test_velocity_is_clamped():
    vx, vy = throw_velocity([(0.0, 0, 0), (0.01, 1000, 1000)], release_t=0.01)
    assert vx == THROW_MAX and vy == THROW_MAX


def _simulate(px, py, vx, vy, steps=2000, dt=1 / 60):
    events, bounced = [], False
    for _ in range(steps):
        px, py, vx, vy, bounced, ev = throw_step(px, py, vx, vy, dt, LO, HI, TOP, GROUND, bounced, G)
        if ev:
            events.append(ev)
        if ev == "landed":
            break
    return px, py, events


def test_keeps_momentum_bounces_off_wall_hops_once_then_lands():
    px, py, events = _simulate(500.0, 300.0, 2500.0, -900.0)
    assert "wall" in events                       # an der rechten Wand abgeprallt
    assert events.count("floor_bounce") == 1      # genau ein Hopser am Boden
    assert events[-1] == "landed" and py == GROUND
    assert LO <= px <= HI


def test_bounces_off_ceiling():
    _, _, events = _simulate(500.0, 50.0, 0.0, -2000.0)
    assert events[0] == "wall"                    # Decke zuerst
    assert events[-1] == "landed"


def test_gentle_drop_lands_without_hop():
    _, _, events = _simulate(500.0, GROUND - 5, 0.0, 0.0)
    assert events == ["landed"]

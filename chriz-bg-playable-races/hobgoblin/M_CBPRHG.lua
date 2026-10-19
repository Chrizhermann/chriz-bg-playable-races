-- Chriz BG Playable Races, hobgoblin: the weapon look right after loading a save.
--
-- Each weapon switches a hobgoblin to the animation for its look code, but only a creature with
-- the spell state HG_HOBGOBLIN_PC, the mark HGPCRACE gives as a timed effect (op328): an equipped
-- op318 shields every other creature from the switch. op318 checks the creature's derived stats.
-- When a save loads, the engine equips the items before it applies the saved effects
-- (CGameSprite::Unmarshal: the derived stats from the creature's base values, the saved effects
-- into the timed effect list, then CGameSpriteEquipment::Unmarshal equips each item and applies
-- its equipped effects at once). So the op318 found the state unset and kept the switch from the
-- hobgoblin too, and every later recalculation of the stats applies the equipped effects before
-- the timed ones again: the switch came only when the weapon was selected anew (lab run 18b).
--
-- EEex calls the listener below right after the saved effects are read, before the items are
-- equipped. A creature whose saved effects set the state gets it in its derived stats there, as
-- its op328 sets it at the next recalculation, and its items are equipped as for any creature
-- with the mark. Nothing is saved; other creatures stay as they are.
--
-- CBPR_HobgoblinLook.Status tells whether this is active, or why not; the console shows it when
-- the game starts.

CBPR_HobgoblinLook = CBPR_HobgoblinLook or {Status = "not started"}
local state = CBPR_HobgoblinLook
if state.queued then return end

local function report(status)
	state.Status = status
	print("Chriz BG Playable Races: hobgoblin weapon look at load " .. status)
end

if not EEex_Active then
	report("off: EEex is not active")
	return
end
state.queued = true

-- The number of HG_HOBGOBLIN_PC in SPLSTATE.IDS, or nil.
local function markerState()
	local found
	EEex_Resource_LoadIDS("SPLSTATE"):iterateUnpackedEntries(function(id, line, start)
		if start:upper() == "HG_HOBGOBLIN_PC" then
			found = id
			return true
		end
	end)
	return found
end

-- Whether a saved effect sets the mark the way op328 does: special not 0 sets the SPLSTATE.IDS
-- state parameter 2 (parameter 1 does not count). Delayed effects (timing 3-8) do not count yet.
local function setsMark(effect, mark)
	local timing = effect.m_durationType
	return effect.m_effectId == 328 and effect.m_special ~= 0 and effect.m_dWFlags == mark
		and (timing < 3 or timing > 8)
end

local function onLoaded(sprite)
	local mark = state.mark
	local found = false
	EEex_Utility_IterateCPtrList(sprite.m_timedEffectList, function(effect)
		found = setsMark(effect, mark)
		return found
	end)
	if not found then return end
	local states = sprite.m_derivedStats.m_spellStates
	local word, bit = math.floor(mark / 32), EEex_LShift(1, mark % 32)
	states:set(word, EEex_BOr(states:get(word), bit))
	if EEex_BAnd(sprite.m_derivedStats.m_spellStates:get(word), bit) == 0 then
		error("the state did not stay set")
	end
end

local function install()
	for _, name in ipairs({"EEex_Resource_LoadIDS", "EEex_Sprite_AddLoadedListener", "EEex_Utility_IterateCPtrList",
			"EEex_BAnd", "EEex_BOr", "EEex_LShift"}) do
		if type(_G[name]) ~= "function" then return "off: this EEex lacks " .. name end
	end
	local mark = markerState()
	if type(mark) ~= "number" or mark < 0 or mark > 255 then
		return "off: SPLSTATE.IDS has no HG_HOBGOBLIN_PC in 0-255"
	end
	state.mark = mark
	EEex_Sprite_AddLoadedListener(function(sprite)
		if state.failed then return end
		local ok, err = pcall(onLoaded, sprite)
		if not ok then
			state.failed = true
			report("off after an error: " .. tostring(err))
		end
	end)
	return "active for spell state " .. mark
end

EEex_GameState_AddInitializedListener(function()
	local ok, status = pcall(install)
	if not ok then status = "off: " .. tostring(status) end
	report(status)
end)

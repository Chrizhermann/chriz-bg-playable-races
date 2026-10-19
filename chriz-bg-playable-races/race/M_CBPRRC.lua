-- Chriz BG Playable Races: races of their own, through EEex.
--
-- The engine takes a race's rules (classes and kits, ability score adjustments and limits, thief
-- skills, infravision, ...) from its race tables, under the label CRuleTables::GetRaceString gives
-- the race. That function knows the labels of the seven standard races only and gives every other
-- race an empty label, so the tables give it their default values: no class in character creation,
-- for one. This hook makes the function answer each race CBPRRACE.2DA lists (row: the label;
-- column ID: the race) with that label, and hands every other race to the original code. EEex's
-- loader finds the function from its code, as CBPR-CRuleTables::GetRaceString
-- (EEex_scripts/extra_pattern_dbs/CBPRRACE.db).
--
-- CBPR_RaceHook.Status tells whether the hook is active, or why not; the console shows it when the
-- game starts.

CBPR_RaceHook = CBPR_RaceHook or {Status = "not started"}
local state = CBPR_RaceHook
if state.queued then return end

local function report(status)
	state.Status = status
	print("Chriz BG Playable Races: race hook " .. status)
end

if not EEex_Active then
	report("off: EEex is not active")
	return
end
state.queued = true

-- The races CBPRRACE.2DA lists, as {id = race, label = text, bio = string reference}. A row is left
-- out when its race cannot have a label of its own (only races 8-255 can, and 153 not: the engine
-- gives it the elf's), when its label is not a word of capital letters, digits and _, and when an
-- earlier row has its race or its label.
local function raceList()
	local races, ids, labels = {}, {}, {}
	local t = EEex_Resource_Load2DA("CBPRRACE")
	local _, rows = t:getDimensions()
	for y = 0, rows - 1 do
		local label = t:getRowLabel(y)
		local id = tonumber(t:getAtLabels("ID", label))
		local bio = tonumber(t:getAtLabels("BIOGRAPHY", label)) or -1
		if id and id == math.floor(id) and id >= 8 and id <= 255 and id ~= 153
				and label:match("^[A-Z_][A-Z0-9_]*$") and not ids[id] and not labels[label] then
			ids[id], labels[label] = true, true
			table.insert(races, {id = id, label = label, bio = bio})
		end
	end
	return races
end

-- The 32-bit displacement at `p`, with its sign.
local function rel32(p)
	local d = EEex_Read32(p)
	if d >= 0x80000000 then d = d - 0x100000000 end
	return d
end

-- The CString(const char *) constructor GetRaceString calls. Each case of the function is
-- "lea rdx, [rip+x]; mov rcx, rbx; call ctor": the seven races' cases copy a static CString, and
-- the default case builds one from an empty C string, with the constructor wanted here. So it is
-- the call target that occurs once and gets a string whose first byte is 0.
local function stringConstructor(fn)
	local cases, calls = {}, {}
	for p = fn, fn + 0x180 do
		if EEex_ReadU8(p) == 0x48 and EEex_ReadU8(p + 1) == 0x8D and EEex_ReadU8(p + 2) == 0x15
				and EEex_ReadU8(p + 7) == 0x48 and EEex_ReadU8(p + 8) == 0x8B and EEex_ReadU8(p + 9) == 0xCB
				and EEex_ReadU8(p + 10) == 0xE8 then
			local c = {src = p + 7 + rel32(p + 3), ctor = p + 15 + rel32(p + 11)}
			table.insert(cases, c)
			calls[c.ctor] = (calls[c.ctor] or 0) + 1
		end
	end
	local found
	for _, c in ipairs(cases) do
		if calls[c.ctor] == 1 and EEex_ReadU8(c.src) == 0 then
			if found then return nil, "two candidates for the string constructor" end
			found = c.ctor
		end
	end
	if not found then return nil, "no string constructor among " .. #cases .. " cases" end
	return found
end

local function bytesAt(address, count)
	local out = {}
	for i = 0, count - 1 do out[#out + 1] = string.format("%02X", EEex_ReadU8(address + i)) end
	return table.concat(out, " ")
end

local function install()
	for _, name in ipairs({"EEex_LabelDefault", "EEex_ReadU8", "EEex_Read32", "EEex_WriteStringCache",
			"EEex_DisableCodeProtection", "EEex_EnableCodeProtection", "EEex_HookShimFunctionMaintainOriginal",
			"EEex_FlattenTable", "EEex_Resource_Load2DA"}) do
		if type(_G[name]) ~= "function" then return "off: this EEex lacks " .. name end
	end
	local races = raceList()
	if #races == 0 then return "off: CBPRRACE.2DA lists no race" end
	local fn = EEex_LabelDefault("CBPR-CRuleTables::GetRaceString", nil)
	if not fn then return "off: EEex's loader did not find CRuleTables::GetRaceString in this game" end
	-- The shim moves the first six bytes (push rbx; sub rsp, 20h), which have no RIP-relative
	-- operand. Other bytes there: another mod hooked the function already, or another game version.
	local prologue = bytesAt(fn, 6)
	if prologue ~= "40 53 48 83 EC 20" then
		return "off: unexpected code at CRuleTables::GetRaceString (" .. prologue .. ")"
	end
	local ctor, why = stringConstructor(fn)
	if not ctor then return "off: " .. why end
	-- One comparison per race (the race is in r8b), else the original code. A listed race: its label
	-- into the CString the caller passes (rdx), which is returned (rax).
	local asm, labels = {}, {}
	for i, race in ipairs(races) do
		table.insert(asm, {"cmp r8b, ", race.id, " #ENDL je cbpr_race_" .. i .. " #ENDL "})
		table.insert(labels, race.label .. " (" .. race.id .. ")")
	end
	table.insert(asm, {"jmp #L(CBPR_GetRaceString_Original) #ENDL "})
	for i, race in ipairs(races) do
		table.insert(asm, {"cbpr_race_" .. i .. ": #ENDL mov r9, ", EEex_WriteStringCache(race.label),
			" #ENDL jmp cbpr_label #ENDL "})
	end
	table.insert(asm, {[[
		cbpr_label: #ENDL
		push rbx #ENDL
		sub rsp, 32 #ENDL
		mov rbx, rdx #ENDL
		mov rdx, r9 #ENDL
		mov rcx, rbx #ENDL
		mov rax, ]], ctor, [[ #ENDL
		call rax #ENDL
		mov rax, rbx #ENDL
		add rsp, 32 #ENDL
		pop rbx #ENDL
		ret #ENDL
	]]})
	EEex_DisableCodeProtection()
	local ok, err = pcall(EEex_HookShimFunctionMaintainOriginal, fn, 6, "CBPR_GetRaceString_Original",
		EEex_FlattenTable(asm))
	EEex_EnableCodeProtection()
	if not ok then return "off: hooking failed: " .. tostring(err) end
	return "active for " .. table.concat(labels, ", ") .. " at " .. string.format("0x%X", fn)
end

EEex_GameState_AddInitializedListener(function()
	local ok, status = pcall(install)
	if not ok then status = "off: " .. tostring(status) end
	state.installed = status:sub(1, 6) == "active"
	report(status)
end)

-- EET builds the race part of the biography in character creation from the Lua table bioRaceData
-- ({race, a biography for each campaign ...}, in M_K#TBL.lua). Each listed race with a biography
-- gets an entry there: the human's, with the race's biography in place of each of the human's.
local function addBiographies()
	if type(bioRaceData) ~= "table" then return end
	local human, have = nil, {}
	for _, e in ipairs(bioRaceData) do
		if type(e) == "table" then
			have[e[1]] = true
			if e[1] == 1 then human = e end
		end
	end
	if not human then return end
	for _, race in ipairs(raceList()) do
		if race.bio >= 0 and not have[race.id] then
			local e = {race.id}
			for i = 2, #human do
				e[i] = (type(human[i]) == "number" and human[i] >= 0) and race.bio or human[i]
			end
			table.insert(bioRaceData, e)
			have[race.id] = true
		end
	end
end

EEex_Menu_AddAfterMainFileLoadedListener(function()
	local ok, err = pcall(addBiographies)
	if not ok then print("Chriz BG Playable Races: biographies: " .. tostring(err)) end
end)

-- For the world scripts: whether party member `slot` (0 = Player1) has a character animation, as
-- character creation gives (ANIMATE.IDS 0x5000-0x6FFF). Character creation and every dual-class
-- give a race the engine has no animation for the human's; a race with a look of its own sets it
-- again then.
function CBPR_HasCharacterAnimation(slot)
	local ok, result = pcall(function()
		local game = EngineGlobals.g_pBaldurChitin.m_pObjectGame
		local sprite = EEex_GameObject_Get(game.m_characters:get(slot))
		if not sprite then return false end
		local anim = sprite.m_baseStats.m_animationType
		return anim >= 0x5000 and anim < 0x7000
	end)
	return ok and result == true
end

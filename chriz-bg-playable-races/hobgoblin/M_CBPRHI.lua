-- Chriz BG Playable Races, hobgoblin: the weapon in the inventory figure.
--
-- The inventory draws a creature from its animation's paperdoll layers (CInfGame::RenderAppearance):
-- body, weapon, shield and helmet, each the BAM <the animation's resref for that layer>INV. A
-- character animation names all four; monster_layered, the hobgoblin's, names its body alone, so
-- the inventory shows the hobgoblin without a weapon. The installer builds one figure per weapon
-- type instead, the hobgoblin standing with that weapon layer (<body><letter>INV), and lists them in
-- CBPRHGIV.2DA: the animation (ID), the first letter of the weapon's look code (LETTER), the figure
-- (FIGURE, without INV). This hook makes the body layer of a listed animation name the figure of
-- the weapon it draws; every other animation and layer, and a hobgoblin without a weapon, keep the
-- engine's answer. EEex's loader finds the two engine functions from their code
-- (EEex_scripts/extra_pattern_dbs/CBPRHG.db); the second one only proves the field offsets below.
--
-- CBPR_HobgoblinInventory.Status tells whether the hook is active, or why not; the console shows it
-- when the game starts.

CBPR_HobgoblinInventory = CBPR_HobgoblinInventory or {Status = "not started"}
local state = CBPR_HobgoblinInventory
if state.queued then return end

local function report(status)
	state.Status = status
	print("Chriz BG Playable Races: hobgoblin inventory figures " .. status)
end

if not EEex_Active then
	report("off: EEex is not active")
	return
end
state.queued = true

-- The rows of CBPRHGIV.2DA, as {id = animation, letter = character code, figure = resref}. A row is
-- left out when its animation is no 16-bit number, its letter not one capital letter or digit, its
-- figure not a resref of at most five characters (the engine appends INV), or an earlier row has
-- its animation and letter.
local function figureList()
	local rows, seen = {}, {}
	local t = EEex_Resource_Load2DA("CBPRHGIV")
	local _, count = t:getDimensions()
	for y = 0, count - 1 do
		local label = t:getRowLabel(y)
		local id = tonumber(t:getAtLabels("ID", label))
		local letter = t:getAtLabels("LETTER", label)
		local figure = t:getAtLabels("FIGURE", label)
		local key = tostring(id) .. ":" .. tostring(letter)
		if id and id == math.floor(id) and id >= 0 and id <= 0xFFFF and type(letter) == "string"
				and letter:match("^[A-Z0-9]$") and type(figure) == "string" and figure:match("^[A-Z0-9_#-]+$")
				and #figure <= 5 and not seen[key] then
			seen[key] = true
			table.insert(rows, {id = id, letter = letter:byte(), figure = figure})
		end
	end
	return rows
end

-- The 32-bit displacement at `p`, with its sign.
local function rel32(p)
	local d = EEex_Read32(p)
	if d >= 0x80000000 then d = d - 0x100000000 end
	return d
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
	local fn = EEex_LabelDefault("CBPR-CGameAnimationTypeMonsterLayered::GetAnimationResRef", nil)
	if not fn then return "off: EEex's loader did not find the paperdoll function of monster_layered" end
	if not EEex_LabelDefault("CBPR-CGameAnimationTypeMonsterLayered::EquipWeapon", nil) then
		return "off: EEex's loader did not find EquipWeapon of monster_layered with the expected fields"
	end
	-- The shim moves the first instruction (mov [rsp+8], rbx), which has no RIP-relative operand.
	-- Other bytes there: another mod hooked the function already.
	local prologue = bytesAt(fn, 5)
	if prologue ~= "48 89 5C 24 08" then
		return "off: unexpected code at the paperdoll function (" .. prologue .. ")"
	end
	-- The function's first call assigns "" to the CString it fills: CString::operator=(const char *).
	local assign = fn + 0x28 + rel32(fn + 0x24)
	local rows = figureList()
	if #rows == 0 then return "off: CBPRHGIV.2DA lists no figure" end
	-- rcx: the animation, rdx: the CString to fill, r8b: the layer. Only the body layer (0) of a
	-- listed animation; its ID (+8) is checked before any field of monster_layered is read. With a
	-- weapon drawn (its cell at +0x1208, which EquipWeapon clears with the index when it draws none),
	-- the code that matched (+0x1740, index at +0x1738) gives the letter, in capitals as the list has
	-- it (the engine matches codes ignoring case), and a listed animation and letter give the figure.
	local ids, asm = {}, {}
	table.insert(asm, {"test r8b, r8b #ENDL jnz #L(CBPR_InvResRef_Original) #ENDL movzx eax, word ptr [rcx+8] #ENDL "})
	for _, row in ipairs(rows) do
		if not ids[row.id] then
			ids[row.id] = true
			table.insert(asm, {"cmp eax, ", row.id, " #ENDL je cbpr_inv_ours #ENDL "})
		end
	end
	table.insert(asm, {[[
		jmp #L(CBPR_InvResRef_Original) #ENDL
		cbpr_inv_ours: #ENDL
		cmp qword ptr [rcx+0x1208], 0 #ENDL
		je #L(CBPR_InvResRef_Original) #ENDL
		movzx r9d, byte ptr [rcx+0x1738] #ENDL
		cmp r9d, 1 #ENDL
		ja #L(CBPR_InvResRef_Original) #ENDL
		shl r9d, 3 #ENDL
		add r9, rcx #ENDL
		mov r9, qword ptr [r9+0x1740] #ENDL
		test r9, r9 #ENDL
		jz #L(CBPR_InvResRef_Original) #ENDL
		movzx r9d, byte ptr [r9] #ENDL
		cmp r9d, 0x61 #ENDL
		jb cbpr_inv_case #ENDL
		cmp r9d, 0x7A #ENDL
		ja cbpr_inv_case #ENDL
		sub r9d, 0x20 #ENDL
		cbpr_inv_case: #ENDL
	]]})
	for i, row in ipairs(rows) do
		table.insert(asm, {"cmp eax, ", row.id, " #ENDL jne cbpr_inv_next_", i, " #ENDL cmp r9d, ", row.letter,
			" #ENDL je cbpr_inv_fig_", i, " #ENDL cbpr_inv_next_", i, ": #ENDL "})
	end
	table.insert(asm, {"jmp #L(CBPR_InvResRef_Original) #ENDL "})
	for i, row in ipairs(rows) do
		table.insert(asm, {"cbpr_inv_fig_", i, ": #ENDL mov r9, ", EEex_WriteStringCache(row.figure),
			" #ENDL jmp cbpr_inv_set #ENDL "})
	end
	table.insert(asm, {[[
		cbpr_inv_set: #ENDL
		push rbx #ENDL
		sub rsp, 32 #ENDL
		mov rbx, rdx #ENDL
		mov rdx, r9 #ENDL
		mov rcx, rbx #ENDL
		mov rax, ]], assign, [[ #ENDL
		call rax #ENDL
		mov rax, rbx #ENDL
		add rsp, 32 #ENDL
		pop rbx #ENDL
		ret #ENDL
	]]})
	EEex_DisableCodeProtection()
	local ok, err = pcall(EEex_HookShimFunctionMaintainOriginal, fn, 5, "CBPR_InvResRef_Original",
		EEex_FlattenTable(asm))
	EEex_EnableCodeProtection()
	if not ok then return "off: hooking failed: " .. tostring(err) end
	local n, figures, seen = 0, 0, {}
	for _ in pairs(ids) do n = n + 1 end
	for _, row in ipairs(rows) do
		if not seen[row.figure] then
			seen[row.figure] = true
			figures = figures + 1
		end
	end
	return "active for " .. n .. " animations (" .. #rows .. " rows of CBPRHGIV.2DA, " .. figures
		.. " figures) at " .. string.format("0x%X", fn)
end

EEex_GameState_AddInitializedListener(function()
	local ok, status = pcall(install)
	if not ok then status = "off: " .. tostring(status) end
	state.installed = status:sub(1, 6) == "active"
	report(status)
end)

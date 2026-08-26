export const buildFloorSlots = (totalFloors, floors = []) => {
  const count = Math.max(0, Number(totalFloors) || 0);
  const available = [...floors];

  const slots = Array.from({ length: count }, (_, offset) => {
    const index = offset + 1;
    const code = `F${String(index).padStart(2, "0")}`;
    const levelOrder = offset;
    const existingIndex = available.findIndex(
      (floor) => floor.levelOrder === levelOrder || floor.code === code,
    );
    const floor = existingIndex >= 0 ? available.splice(existingIndex, 1)[0] : null;

    return { index, code, levelOrder, floor };
  });

  slots.forEach((slot) => {
    if (!slot.floor && available.length) slot.floor = available.shift();
  });
  return slots;
};

export const floorCreationPayload = (slot, name, floorType) => ({
  code: slot.code,
  name: name.trim(),
  levelOrder: slot.levelOrder,
  floorType,
});

export const getFloorRegistrationState = (totalFloors, floors = []) => {
  const slots = buildFloorSlots(totalFloors, floors);
  const registeredCount = slots.filter(
    ({ floor }) => Boolean(floor?.id) && Boolean(floor.name?.trim()),
  ).length;

  return {
    totalCount: slots.length,
    registeredCount,
    missingCount: Math.max(0, slots.length - registeredCount),
    isComplete: slots.length > 0 && registeredCount === slots.length,
  };
};

// Keep the persisted route identifier compatible with existing desktop settings.
export function routeDisplayName(name: string): string {
  return name === 'default' ? '思源湖' : name;
}

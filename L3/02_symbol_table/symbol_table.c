#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define BUCKETS 101

typedef struct Entry {
  char *value;
  int id;
  int type; /* 0: identifier, 1: Boolean constant, 2: state constant */
  struct Entry *next;
} Entry;

typedef struct {
  Entry *buckets[BUCKETS];
  int size;
} SymbolTable;

static unsigned hash(const char *value) {
  uint32_t h = 2166136261u;
  while (*value) {
    h ^= (unsigned char)*value++;
    h *= 16777619u;
  }
  return h % BUCKETS;
}

SymbolTable *st_create(void) { return calloc(1, sizeof(SymbolTable)); }

int st_lookup(const SymbolTable *table, const char *value) {
  for (Entry *e = table->buckets[hash(value)]; e; e = e->next)
    if (strcmp(e->value, value) == 0)
      return e->id;
  return -1;
}

/* Return the existing/new stable ID, or -1 on allocation failure. */
int st_insert(SymbolTable *table, const char *value, int type) {
  int existing = st_lookup(table, value);
  if (existing >= 0)
    return existing;
  Entry *e = malloc(sizeof(*e));
  if (!e)
    return -1;
  e->value = malloc(strlen(value) + 1);
  if (!e->value) {
    free(e);
    return -1;
  }
  strcpy(e->value, value);
  unsigned bucket = hash(value);
  e->type = type;
  e->id = table->size++;
  e->next = table->buckets[bucket];
  table->buckets[bucket] = e;
  return e->id;
}

int st_size(const SymbolTable *table) { return table->size; }

const char *st_value(const SymbolTable *table, int id) {
  for (unsigned b = 0; b < BUCKETS; ++b)
    for (Entry *e = table->buckets[b]; e; e = e->next)
      if (e->id == id)
        return e->value;
  return NULL;
}

int st_type(const SymbolTable *table, int id) {
  for (unsigned b = 0; b < BUCKETS; ++b)
    for (Entry *e = table->buckets[b]; e; e = e->next)
      if (e->id == id)
        return e->type;
  return -1;
}

void st_destroy(SymbolTable *table) {
  if (!table)
    return;
  for (unsigned b = 0; b < BUCKETS; ++b) {
    Entry *e = table->buckets[b];
    while (e) {
      Entry *next = e->next;
      free(e->value);
      free(e);
      e = next;
    }
  }
  free(table);
}

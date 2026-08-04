# UUIDv4 vs UUIDv7

UUIDs (Universally Unique Identifiers) are 128-bit identifiers commonly used in databases, distributed systems, APIs, and applications where globally unique IDs are needed without central coordination.

UUIDv4 and UUIDv7 serve different design goals.

- UUIDv4 prioritizes randomness
- UUIDv7 prioritizes time ordering plus randomness

UUIDv7 is relatively new and was standardized in RFC 9562 in 2024.

## Quick Comparison

| Feature                    | UUIDv4                        | UUIDv7                         |
| -------------------------- | ----------------------------- | ------------------------------ |
| Primary basis              | Random                        | Timestamp + random             |
| Sortable by creation time  | No                            | Yes                            |
| Database index locality    | Poor                          | Good                           |
| Predictability             | Very low                      | Slightly more predictable      |
| Collision probability      | Extremely low                 | Extremely low                  |
| Widely supported           | Very mature                   | Growing support                |
| Human debugging usefulness | Low                           | Better                         |
| Distributed generation     | Excellent                     | Excellent                      |
| Privacy leakage            | Minimal                       | Timestamp exposed              |
| Best use cases             | Security-sensitive random IDs | Databases, logs, event systems |

------

# UUIDv4

## How UUIDv4 Works

UUIDv4 is almost entirely random.

It uses:

- 122 random bits
- 6 reserved/version bits

Example:

```text
550e8400-e29b-41d4-a716-446655440000
```

The `4` indicates version 4.

## Advantages of UUIDv4

### Excellent Randomness

UUIDv4 identifiers are highly unpredictable.

Good for:

- Public-facing identifiers
- Security-sensitive APIs
- Session tokens (sometimes)
- Multi-tenant systems

### Extremely Low Collision Risk

Even with billions of generated UUIDs, collisions are astronomically unlikely.

### Mature Ecosystem Support

UUIDv4 is supported almost everywhere:

- PostgreSQL
- MySQL
- SQLite
- Python
- JavaScript
- Go
- Java
- Rust
- Kubernetes
- Cloud systems

### No Time Information Leakage

UUIDv4 does not reveal:

- Creation time
- Server order
- Throughput patterns

This can improve operational privacy.

------

## Disadvantages of UUIDv4

### Poor Database Index Performance

Random insertion causes index fragmentation.

In B-tree indexes:

- Inserts happen randomly
- Pages split frequently
- Cache locality suffers

This can reduce:

- Insert performance
- Read efficiency
- Replication efficiency

Especially problematic at scale.

### No Natural Ordering

You cannot sort UUIDv4 values chronologically.

This complicates:

- Event ordering
- Cursor pagination
- Log analysis
- Time-based debugging

### Harder Operational Debugging

Looking at a UUIDv4 gives no useful context.

------

# UUIDv7

## How UUIDv7 Works

UUIDv7 combines:

- Unix timestamp in milliseconds
- Random bits

Example structure:

```text
018f0d9e-7b6e-7cc8-b1a3-6d5f1d8e9c12
```

The `7` indicates version 7.

The beginning encodes time, making UUIDs sortable by creation order.

RFC 9562 standardized UUIDv7 to solve practical database and distributed-system problems.

------

## Advantages of UUIDv7

### Time-Ordered

UUIDv7 values sort naturally by creation time.

This is extremely useful for:

- Event systems
- Logs
- Message queues
- Analytics
- Time-series data
- Pagination

### Better Database Performance

UUIDv7 improves index locality.

Benefits include:

- Fewer B-tree page splits
- Better cache performance
- Faster inserts
- Reduced fragmentation

This is one of the biggest reasons modern systems adopt UUIDv7.

### Better for Distributed Systems

You still get decentralized ID generation without requiring:

- Central counters
- Database sequences
- Coordination services

But you also gain temporal ordering.

### Easier Debugging

You can often infer:

- Rough creation time
- Event sequence

This simplifies operations and troubleshooting.

### Better for Write-Heavy Systems

UUIDv7 performs especially well in:

- PostgreSQL
- MySQL/InnoDB
- Cassandra-like systems
- Event sourcing systems

------

## Disadvantages of UUIDv7

### Timestamp Leakage

UUIDv7 exposes creation timing.

An attacker may infer:

- Approximate object creation time
- System activity rates
- Traffic patterns

This may matter in:

- Privacy-sensitive systems
- Security-sensitive APIs

### Slightly More Predictable

Although still highly random, UUIDv7 is not as opaque as UUIDv4.

The timestamp portion is known.

### Newer Ecosystem Support

Support is growing quickly, but not universal yet.

Some older libraries:

- Only support UUIDv4
- Require upgrades
- Lack native UUIDv7 generation

### Clock Dependence

UUIDv7 depends partly on system clocks.

Potential issues:

- Clock drift
- Clock rollback
- Time synchronization problems

Good implementations mitigate this carefully.

------

# Real-World Database Impact

## UUIDv4 Insert Pattern

Random insertion:

```text
Insert → random page
Insert → another random page
Insert → another random page
```

This fragments indexes heavily.

------

## UUIDv7 Insert Pattern

Mostly sequential insertion:

```text
Insert → end of index
Insert → near end
Insert → near end
```

This behaves similarly to auto-increment IDs while remaining globally unique.

------

# Security Considerations

## UUIDv4

Better when:

- IDs are public
- Enumeration resistance matters
- Timing metadata should remain hidden

## UUIDv7

Usually fine for:

- Internal systems
- Databases
- Logging
- Distributed event systems

But evaluate timestamp exposure carefully.

------

# Modern Recommendation

## Choose UUIDv4 When

You prioritize:

- Maximum unpredictability
- Privacy
- Mature compatibility
- Public-facing identifiers

Examples:

- User-facing URLs
- Public APIs
- Security-sensitive systems

------

## Choose UUIDv7 When

You prioritize:

- Database performance
- Sortability
- Operational simplicity
- High insert throughput

Examples:

- PostgreSQL primary keys
- Event sourcing
- Logging systems
- Distributed services
- Analytics platforms

------

# Hybrid Approaches

Some systems use both:

| Purpose                 | UUID Type |
| ----------------------- | --------- |
| Internal DB primary key | UUIDv7    |
| Public external ID      | UUIDv4    |

This combines:

- Efficient storage/indexing
- Public unpredictability

------

# Comparison to Auto-Increment IDs

UUIDv7 is often viewed as a compromise between:

| Feature          | Auto Increment | UUIDv4    | UUIDv7    |
| ---------------- | -------------- | --------- | --------- |
| Sequential       | Yes            | No        | Mostly    |
| Globally unique  | No             | Yes       | Yes       |
| Distributed-safe | Poor           | Excellent | Excellent |
| DB locality      | Excellent      | Poor      | Good      |
| Predictability   | High           | Low       | Medium    |

------

# Current Industry Trend

Many modern systems are moving toward:

- UUIDv7
- ULID
- KSUID
- Snowflake-style IDs

The common goal is:

> Globally unique identifiers with time ordering.

UUIDv7 is becoming particularly attractive because it is now officially standardized.

------

# References

## RFC

- Peabody, B., & Davis, K. (2024). *RFC 9562: Universally Unique IDentifiers (UUIDs)*. Internet Engineering Task Force (IETF). https://www.rfc-editor.org/rfc/rfc9562

## PostgreSQL Discussion

- PostgreSQL Documentation. *UUID Type*. https://www.postgresql.org/docs/current/datatype-uuid.html

## ULID Specification

- ULID Specification. https://github.com/ulid/spec

## Additional Reading

- Cloudflare Engineering. *UUIDs are Bad for Database Index Performance*. https://blog.cloudflare.com/the-problem-with-eventually-consistent-databases-and-how-cloudflare-handles-it/
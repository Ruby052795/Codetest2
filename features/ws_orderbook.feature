@Websocket_Market_Data_Subscriptions
Feature: WebSocket orderbook API

  Background:
    Given WebSocket book API is connected successfully

  @subscription @Orderbook @success
  Scenario Outline: TC-01, TC-02, TC-03, TC-04 - Successful Subscription scenario
    When I send a subscription request: channels="<channel>", subscription_type="<subscription_type>", update_frequency="<update_frequency>"
    When I waited and received the 2 snapshot response
    Then I should receive a response said Successful Subscription
    And I should receive a snapshot response
    And "depth" in snapshot response should be: <depth>
    And "instrument_name" in snapshot response should be: BTCUSD-PERP

    Examples:
      | channel            | subscription_type        | update_frequency | depth |
      | book.BTCUSD-PERP.10 | SNAPSHOT                | 500              | 10    |
      | book.BTCUSD-PERP.50 | SNAPSHOT                | 500              | 50    |
      | book.BTCUSD-PERP.10 | SNAPSHOT_AND_UPDATE     | 10               | 10    |
      | book.BTCUSD-PERP.50 | SNAPSHOT_AND_UPDATE     | 100              | 50    |

  @subscription @failure
  Scenario Outline: TC-05, TC-06, TC-07, TC-08, TC-09 - Failed Subscription scenario
    When I send a subscription request: channels="<channel>", subscription_type="<subscription_type>", update_frequency="<update_frequency>"
    Then Subscription request is sent failed

    Examples:
      | channel                 | subscription_type       | update_frequency |
      | book.INVALID-SYMBOL.10  | SNAPSHOT                | 500  |
      | book.BTCUSD-PERP.25     | SNAPSHOT                | 500  |
      | book.BTCUSD-PERP.10     | INVALID_TYPE            | 500  |
      | book.BTCUSD-PERP.10     | SNAPSHOT_AND_UPDATE     | 50   |
      | book.BTCUSD-PERP.10     | SNAPSHOT                | 10   |

  @snapshot @TC10 @TC11
  Scenario: TC-10, TC-11 - SNAPSHOT Mode Behavior and Data Validation
    Given I subscribed to "book.BTCUSD-PERP.10" (SNAPSHOT) mode
    When received and collect snapshot messages for 3s
    And I re-subscribed the same request with depth value changed (TC-11)
    Then The second snapshot response should be a valid snapshot message
    And The time interval between messages should be close to 500ms
    And The data structure of the snapshot should be correct

   # in sandbox, delta subscription only receive heartbeat packages
  @delta @TC12 @TC13
  Scenario: TC-12, TC-13 - DELTA Mode Updates and Sequence Validation
    Given I subscribed to "book.BTCUSD-PERP.50" (SNAPSHOT_AND_UPDATE) mode
    When I stored the u field of the snapshot response
    And received and collect delta messages for 3s
    And I re-subscribed the same request with depth value changed (TC-13)
    Then The time interval between messages should be close to 100ms
    And The u and pu sequences must remain continuous
    And The data structure of the delta should be correct


  @delta @TC14
  Scenario: TC-14 - DELTA Mode Heartbeat Packet Detection
    Given I subscribed to "book.BTCUSD-PERP.10" (SNAPSHOT_AND_UPDATE) mode
    When I stored the u field of the snapshot response
    And I wait up to 5 seconds to receive a heartbeat package
    Then I should have received a heartbeat message

  @recovery @TC15 @TC16
  Scenario: TC-15, TC-16 - DELTA Sequence Mismatch and Recovery
    Given I subscribed to "book.BTCUSD-PERP.10" (SNAPSHOT_AND_UPDATE) mode
    When I waited and received the next delta response
    And I stored the u field of the snapshot response
    And Intentionally set the locally stored u sequence to "BAD_SEQUENCE"
    And I waited and received the next delta response
    Then I detected sequences mismatch
    When Re-subscribed the same request
    Then I should receive a response said Successful Subscription
    And I should receive a snapshot response

  @recovery @TC17
  Scenario: TC-17 - Duplicate Subscription
    Given I subscribed to "book.BTCUSD-PERP.10" (SNAPSHOT) mode
    And I am spy on send methods
    When Re-subscribed the same request
    Then No unsubscribe message sent
    And I should receive a response said Successful Subscription